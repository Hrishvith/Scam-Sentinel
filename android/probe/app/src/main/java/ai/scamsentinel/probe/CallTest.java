package ai.scamsentinel.probe;

import android.content.Context;
import android.content.SharedPreferences;
import android.media.AudioDeviceInfo;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Build;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Locale;
import java.util.function.Consumer;

/**
 * The call test: records 4 seconds from each microphone source an app may use and measures how loud each
 * one was. Android 10+ gives ordinary apps silence during a call; an enabled accessibility service may
 * capture (developer.android.com/media/platform/sharing-audio-input), which is what this checks.
 */
final class CallTest {
    static final int RATE = 16000;
    static final int SECONDS = 4;
    static final int[] SOURCES = {MediaRecorder.AudioSource.MIC, MediaRecorder.AudioSource.VOICE_RECOGNITION,
            MediaRecorder.AudioSource.VOICE_COMMUNICATION, MediaRecorder.AudioSource.CAMCORDER,
            MediaRecorder.AudioSource.UNPROCESSED};
    static final String[] NAMES = {"MIC", "VOICE_RECOGNITION", "VOICE_COMMUNICATION", "CAMCORDER", "UNPROCESSED"};
    private static volatile boolean running = false;

    private CallTest() { }

    static boolean inCall(Context c) {
        int mode = ((AudioManager) c.getSystemService(Context.AUDIO_SERVICE)).getMode();
        return mode == AudioManager.MODE_IN_CALL || mode == AudioManager.MODE_IN_COMMUNICATION;
    }

    /** Which device the call is using: the speaker is needed so the microphone can hear the other person. */
    static String callDevice(Context c) {
        AudioManager am = (AudioManager) c.getSystemService(Context.AUDIO_SERVICE);
        if (Build.VERSION.SDK_INT >= 31) {
            AudioDeviceInfo d = am.getCommunicationDevice();
            if (d == null) return "unknown";
            switch (d.getType()) {
                case AudioDeviceInfo.TYPE_BUILTIN_SPEAKER: return "speaker ON";
                case AudioDeviceInfo.TYPE_BUILTIN_EARPIECE: return "earpiece (speaker OFF)";
                case AudioDeviceInfo.TYPE_BLUETOOTH_SCO: return "Bluetooth headset";
                case AudioDeviceInfo.TYPE_WIRED_HEADSET: case AudioDeviceInfo.TYPE_WIRED_HEADPHONES: return "wired headset";
                default: return "device type " + d.getType();
            }
        }
        return am.isSpeakerphoneOn() ? "speaker ON" : "speaker OFF";
    }

    /** Runs the test once (only during a call). `say` shows progress on the floating button. */
    static void run(Context c, Consumer<String> say) {
        if (running) return;
        if (!inCall(c)) { say.accept("📞 Start a call first,\nthen turn on speaker\nand tap here."); return; }
        running = true;
        try {
            boolean a11y = SentinelAccessibility.isOn();
            StringBuilder report = new StringBuilder();
            report.append(String.format(Locale.US, "Android %s (API %d), %s %s\n", Build.VERSION.RELEASE, Build.VERSION.SDK_INT,
                    Build.MANUFACTURER, Build.MODEL));
            report.append("During a call: yes · audio: ").append(callDevice(c)).append("\n");
            report.append("Accessibility service: ").append(a11y ? "ON" : "OFF").append("\n\n");
            double best = -200; String bestName = "";
            for (int i = 0; i < SOURCES.length; i++) {
                say.accept(String.format(Locale.US, "Testing %d/%d…\nOther person: keep talking.\nYou: stay quiet.", i + 1, SOURCES.length));
                double db = record(SOURCES[i], new File(c.getFilesDir(), NAMES[i] + ".wav"));
                String verdict = db <= -199 ? "BLOCKED" : db <= -119 ? "zeros (muted by Android)" : db < -60 ? "silence"
                        : db < -45 ? "very quiet" : "HEARD SOUND";
                report.append(String.format(Locale.US, "%-20s %6.1f dB  %s\n", NAMES[i], db, verdict));
                if (db > best) { best = db; bestName = NAMES[i]; }
            }
            String summary = best >= -45
                    ? "Sound was heard (" + bestName + "). Press ▶ and check it is the OTHER person's voice."
                    : a11y ? "Still silence with the accessibility service. This phone blocks apps from hearing calls."
                           : "Silence. Turn on the accessibility service (step 4) and test again.";
            report.append("\n").append(summary);
            SharedPreferences prefs = c.getSharedPreferences("probe", Context.MODE_PRIVATE);
            prefs.edit().putString("report", report.toString()).apply();
            say.accept(best >= -45 ? "✅ Done: sound heard.\nOpen the app to listen." : "❌ Done: only silence.\nOpen the app.");
        } finally {
            running = false;
        }
    }

    /** Records SECONDS seconds from one source into a WAV file; returns the loudness in dBFS (-200 if blocked). */
    private static double record(int source, File out) {
        int min = AudioRecord.getMinBufferSize(RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        AudioRecord rec;
        try {
            rec = new AudioRecord(source, RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, Math.max(min, RATE));
        } catch (Exception e) { return -200; }
        if (rec.getState() != AudioRecord.STATE_INITIALIZED) { rec.release(); return -200; }
        short[] pcm = new short[RATE * SECONDS];
        int got = 0;
        try {
            rec.startRecording();
            if (rec.getRecordingState() != AudioRecord.RECORDSTATE_RECORDING) { rec.release(); return -200; }
            while (got < pcm.length) {
                int n = rec.read(pcm, got, Math.min(1600, pcm.length - got));
                if (n <= 0) break;
                got += n;
            }
            rec.stop();
        } catch (Exception e) { got = 0; }
        rec.release();
        if (got == 0) return -200;
        double sum = 0;
        for (int i = 0; i < got; i++) sum += (double) pcm[i] * pcm[i];
        double rms = Math.sqrt(sum / got);
        writeWav(out, pcm, got);
        return rms < 1 ? -120 : 20 * Math.log10(rms / 32768.0);
    }

    private static void writeWav(File out, short[] pcm, int n) {
        int bytes = n * 2;
        byte[] b = new byte[44 + bytes];
        java.nio.ByteBuffer h = java.nio.ByteBuffer.wrap(b).order(java.nio.ByteOrder.LITTLE_ENDIAN);
        h.put("RIFF".getBytes()).putInt(36 + bytes).put("WAVE".getBytes()).put("fmt ".getBytes()).putInt(16)
         .putShort((short) 1).putShort((short) 1).putInt(RATE).putInt(RATE * 2).putShort((short) 2).putShort((short) 16)
         .put("data".getBytes()).putInt(bytes);
        for (int i = 0; i < n; i++) h.putShort(pcm[i]);
        try (FileOutputStream f = new FileOutputStream(out)) { f.write(b); } catch (IOException ignored) { }
    }
}
