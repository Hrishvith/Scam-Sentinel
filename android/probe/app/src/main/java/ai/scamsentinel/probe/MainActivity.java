package ai.scamsentinel.probe;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;

/** Three steps (microphone, draw over other apps, start), then the result of the call test. */
public class MainActivity extends Activity {
    private LinearLayout box;
    private TextView status, result;
    private MediaPlayer player;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        ScrollView scroll = new ScrollView(this);
        box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(40, 60, 40, 60);
        scroll.addView(box);
        setContentView(scroll);

        text("Scam Sentinel · call test", 26, true);
        text("Finds out if this phone lets an app hear the other person during a normal call. "
                + "Nothing is sent anywhere: the test recordings stay on this phone.", 16, false);
        status = text("", 17, true);

        button("1. Allow the microphone", v -> {
            if (Build.VERSION.SDK_INT >= 33)
                requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO, Manifest.permission.POST_NOTIFICATIONS}, 1);
            else requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1);
        });
        button("2. Allow \"draw over other apps\"", v -> startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName()))));
        button("3. Show the 🛡️ test button", v -> {
            if (!ready()) { refresh(); return; }
            startForegroundService(new Intent(this, ProbeService.class));
            status.setText("✅ The 🛡️ button is on screen. Now make the test call (below).");
        });
        text("Then:\n• From ANOTHER phone, call this phone with the normal dialler and answer.\n"
                + "• Turn on SPEAKER.\n• Tap 🛡️ Test this call (it floats over the call screen).\n"
                + "• The other person talks for 20 seconds. You stay quiet.\n• After the call, open this app again.", 16, false);
        result = text("", 15, false);
        result.setTypeface(Typeface.MONOSPACE);
        for (String name : ProbeService.NAMES) {
            button("▶ Play what " + name + " heard", v -> play(new File(getFilesDir(), name + ".wav")));
        }
        button("Stop the test button", v -> stopService(new Intent(this, ProbeService.class)));
    }

    @Override protected void onResume() { super.onResume(); refresh(); }

    private boolean ready() {
        return checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
                && Settings.canDrawOverlays(this);
    }

    private void refresh() {
        boolean mic = checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
        boolean overlay = Settings.canDrawOverlays(this);
        status.setText((mic ? "✅" : "⬜") + " Microphone allowed\n" + (overlay ? "✅" : "⬜") + " Draw over other apps allowed");
        String report = getSharedPreferences("probe", MODE_PRIVATE).getString("report", "");
        result.setText(report.isEmpty() ? "No test yet." : "Last test:\n" + report);
    }

    private void play(File f) {
        if (!f.exists()) { result.append("\n(no recording yet for " + f.getName() + ")"); return; }
        if (player != null) player.release();
        player = MediaPlayer.create(this, Uri.fromFile(f));
        if (player != null) player.start();
    }

    private TextView text(String s, int size, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s); t.setTextSize(size); t.setPadding(0, 16, 0, 16);
        if (bold) t.setTypeface(Typeface.DEFAULT_BOLD);
        box.addView(t);
        return t;
    }

    private void button(String s, android.view.View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(s); b.setTextSize(17); b.setAllCaps(false); b.setOnClickListener(l);
        box.addView(b, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
    }
}
