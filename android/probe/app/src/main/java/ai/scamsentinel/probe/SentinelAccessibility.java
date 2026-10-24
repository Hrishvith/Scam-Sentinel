package ai.scamsentinel.probe;

import android.accessibilityservice.AccessibilityService;
import android.graphics.PixelFormat;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.widget.TextView;

/**
 * Accessibility service used ONLY so Android lets this app hear a call on speaker (Android 10+ allows an
 * accessibility service to capture audio during a call). It reads no screen content and handles no events.
 * While it is on, the floating test button is drawn as an accessibility overlay, which keeps it on top.
 */
public class SentinelAccessibility extends AccessibilityService {
    private static volatile SentinelAccessibility instance;
    private TextView bubble;
    private final Handler ui = new Handler(Looper.getMainLooper());

    static boolean isOn() { return instance != null; }

    @Override
    protected void onServiceConnected() {
        instance = this;
        WindowManager wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        bubble = new TextView(this);
        bubble.setText("🛡️ Test this call");
        bubble.setTextSize(20);
        bubble.setTextColor(0xFFFFFFFF);
        bubble.setBackgroundColor(0xEE0B5D4B);
        bubble.setPadding(36, 28, 36, 28);
        bubble.setOnClickListener(v -> new Thread(() -> CallTest.run(this, this::say)).start());
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, PixelFormat.TRANSLUCENT);
        lp.gravity = Gravity.TOP | Gravity.END;
        lp.y = 220;
        wm.addView(bubble, lp);
    }

    private void say(String text) {
        ui.post(() -> { if (bubble != null) bubble.setText(text); });
        ui.postDelayed(() -> { if (bubble != null && text.startsWith("📞")) bubble.setText("🛡️ Test this call"); }, 4000);
    }

    @Override public void onAccessibilityEvent(AccessibilityEvent event) { }
    @Override public void onInterrupt() { }

    @Override
    public void onDestroy() {
        if (bubble != null) ((WindowManager) getSystemService(WINDOW_SERVICE)).removeView(bubble);
        bubble = null;
        instance = null;
        super.onDestroy();
    }
}
