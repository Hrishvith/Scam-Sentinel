package ai.scamsentinel.probe;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.TextView;

/**
 * Keeps the microphone allowed while the dialer is in front (a foreground service started from the open app)
 * and, when the accessibility service is off, shows the floating test button over other apps.
 */
public class ProbeService extends Service {
    private WindowManager windows;
    private TextView bubble;
    private final Handler ui = new Handler(Looper.getMainLooper());

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startInForeground();
        if (bubble == null && !SentinelAccessibility.isOn()) showBubble();   // the accessibility service draws its own
        return START_NOT_STICKY;
    }

    private void startInForeground() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("probe", "Call test", NotificationManager.IMPORTANCE_LOW));
        Notification n = new Notification.Builder(this, "probe")
                .setContentTitle("Scam Sentinel call test is ready")
                .setContentText("During a call on speaker, tap the shield button")
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
        bubble.setOnClickListener(v -> new Thread(() -> CallTest.run(this, this::say)).start());
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, PixelFormat.TRANSLUCENT);
        lp.gravity = Gravity.TOP | Gravity.END;
        lp.y = 220;
        windows.addView(bubble, lp);
    }

    private void say(String text) {
        ui.post(() -> { if (bubble != null) bubble.setText(text); });
        ui.postDelayed(() -> { if (bubble != null && text.startsWith("📞")) bubble.setText("🛡️ Test this call"); }, 4000);
    }

    @Override
    public void onDestroy() {
        if (bubble != null && windows != null) windows.removeView(bubble);
        bubble = null;
        super.onDestroy();
    }
}
