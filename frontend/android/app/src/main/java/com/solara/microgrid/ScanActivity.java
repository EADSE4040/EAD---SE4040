package com.solara.microgrid;

import android.app.Activity;
import android.graphics.Color;
import android.widget.Button;
import android.widget.LinearLayout;
import com.journeyapps.barcodescanner.CaptureActivity;
import com.journeyapps.barcodescanner.DecoratedBarcodeView;

/** Camera scanning with an explicit cancellation button. */
public final class ScanActivity extends CaptureActivity {
  @Override
  protected DecoratedBarcodeView initializeContent() {
    LinearLayout root = new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setBackgroundColor(Color.rgb(32, 93, 70));
    root.setOnApplyWindowInsetsListener((view, insets) -> {
      view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
          insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
      return insets;
    });
    Button back = new Button(this);
    back.setText("\u2039 Back to Solara");
    back.setAllCaps(false);
    back.setTextColor(Color.WHITE);
    back.setBackgroundColor(Color.TRANSPARENT);
    back.setContentDescription("Cancel QR scan and go back");
    back.setOnClickListener(view -> {
      setResult(Activity.RESULT_CANCELED);
      finish();
    });
    root.addView(back, new LinearLayout.LayoutParams(-1,
        Math.round(56 * getResources().getDisplayMetrics().density)));
    DecoratedBarcodeView scanner = new DecoratedBarcodeView(this);
    root.addView(scanner, new LinearLayout.LayoutParams(-1, 0, 1));
    setContentView(root);
    root.requestApplyInsets();
    return scanner;
  }
}
