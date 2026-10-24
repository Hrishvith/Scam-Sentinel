package ai.scamsentinel.probe;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.graphics.PixelFormat;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Locale;

/**
 * Shows a floating "Test this call" button over every app (needs "draw over other apps").
 * Tapping it records 4 seconds from each microphone source Android offers to ordinary apps and measures
 * how loud each one was, to find out whether this phone lets an app hear the other side of a normal call.
 * Started from the open app, so the microphone stays allowed while the dialer is in front.
 */
public class ProbeService extends Service {
    static final int RATE = 16000;
    static final int SECONDS = 4;
    static final int[] SOURCES = {MediaRecorder.AudioSource.MIC, MediaRecorder.AudioSource.VOICE_RECOGNITION,
            MediaRecorder.AudioSource.VOICE_COMMUNICATION, MediaRecorder.AudioSource.CAMCORDER,
            MediaRecorder.AudioSource.UNPROCESSED};
    static final String[] NAMES = {"MIC", "VOICE_RECOGNITION", "VOICE_COMMUNICATION", "CAMCORDER", "UNPROCESSED"};

    private WindowManager windows;
    private TextView bubble;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile boolean testing = false;

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startInForeground();
        if (bubble == null) showBubble();
        return START_NOT_STICKY;
    }

    private void startInForeground() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("probe", "Call test", NotificationManager.IMPORTANCE_LOW));
        Notification n = new Notification.Builder(this, "probe")
                .setContentTitle("Scam Sentinel call test is ready")
                .setContentText("Tap the shield button during a call on speaker")
                .setSmallIcon(android.R.drawable.ic_lock_lock)
                .build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        else startForeground(1, n);
    }

    private void showBubble() {
        windows = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
        bubble = new TextView(this);
        bubble.setText("🛡️ Test this call");
        bubble.setTextSize(20);
        bubble.setTextColor(0xFFFFFFFF);
        bubble.setBackgroundColor(0xEE0B5D4B);
        bubble.setPadding(36, 28, 36, 28);
        bubble.setOnClickListener(v -> { if (!testing) new Thread(this::runTest).start(); });
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, PixelFormat.TRANSLUCENT);
        lp.gravity = Gravity.TOP | Gravity.END;
        lp.y = 220;
        windows.addView(bubble, lp);
    }

    private void say(String text) { ui.post(() -> { if (bubble != null) bubble.setText(text); }); }

    private void runTest() {
        testing = true;
        AudioManager am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        int mode = am.getMode();
        boolean inCall = mode == AudioManager.MODE_IN_CALL || mode == AudioManager.MODE_IN_COMMUNICATION;
        StringBuilder report = new StringBuilder();
        report.append(String.format(Locale.US, "Android %s (API %d), %s %s\n", Build.VERSION.RELEASE, Build.VERSION.SDK_INT,
                Build.MANUFACTURER, Build.MODEL));
        report.append("During a call: ").append(inCall ? "yes" : "NO (start the test while on a call)")
              .append(" · speaker: ").append(am.isSpeakerphoneOn() ? "on" : "off / unknown").append("\n\n");
        double best = -200; String bestName = "";
        for (int i = 0; i < SOURCES.length; i++) {
            say(String.format(Locale.US, "Testing %d/%d…\nOther person: keep talking.\nYou: stay quiet.", i + 1, SOURCES.length));
            double db = record(SOURCES[i], new File(getFilesDir(), NAMES[i] + ".wav"));
            String verdict = db <= -199 ? "BLOCKED (could not record)" : db < -60 ? "silence" : db < -45 ? "very quiet" : "HEARD SOUND";
            report.append(String.format(Locale.US, "%-20s %6.1f dB  %s\n", NAMES[i], db, verdict));
            if (db > best) { best = db; bestName = NAMES[i]; }
        }
        String summary = best >= -45
                ? "Sound was heard (" + bestName + "). Open the app and press ▶ to check it is the OTHER person's voice."
                : "Only silence. This phone does not let apps hear calls.";
        report.append("\n").append(summary);
        SharedPreferences prefs = getSharedPreferences("probe", MODE_PRIVATE);
        prefs.edit().putString("report", report.toString()).apply();
        say(best >= -45 ? "✅ Done: sound heard.\nOpen the app to listen." : "❌ Done: only silence.\nOpen the app.");
        testing = false;
    }

    /** Records SECONDS seconds from one source into a WAV file; returns the loudness in dBFS (-200 if blocked). */
    private double record(int source, File out) {
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

    @Override
    public void onDestroy() {
        if (bubble != null && windows != null) windows.removeView(bubble);
        bubble = null;
        super.onDestroy();
    }
}
