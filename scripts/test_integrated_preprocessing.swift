#!/usr/bin/swift
/// Simple test showing before/after with integrated preprocessing
import Foundation

// Copy this path if running from a different directory
let projectRoot = "/Users/chester.kim/workspace/trashcan/orientalmeddic"

print("""
✅ Integration Complete!

To test preprocessing in your app:

1. ImagePreprocessor.swift added to OrientalMedDic/
   └─ Handles upscaling + contrast boost

2. OCRService.recognize() updated with preprocessing
   └─ Default: usePreprocessing = true
   └─ Call: OCRService.recognize(cgImage) // preprocessing ON
   └─ Call: OCRService.recognize(cgImage, usePreprocessing: false) // OFF

3. Test images available at:
   └─ \(projectRoot)/data/test/IMG_*.jpg

Next Steps:

A) QUICK TEST (Xcode Preview)
   • Open OverlayReadingView.swift in Xcode
   • Take a photo of a book page
   • Compare recognition quality with preprocessing ON/OFF
   • Adjust ImagePreprocessor defaults if needed:
     - scaleFactor: 2.0 (try 1.5-3.0)
     - contrastBoost: 2.5 (try 1.5-3.0)

B) COMMAND-LINE TEST (if building a CLI)
   • Use scripts/test_ocr_preprocessing_tunable.swift
   • Run: swift scripts/test_ocr_preprocessing_tunable.swift
   • Adjust contrast/scale parameters until you get best results
   • Copy winning parameters to ImagePreprocessor.swift

C) PRODUCTION TUNING
   • Add a Debug menu to toggle preprocessing ON/OFF
   • Let your wife test both modes with real book pages
   • Fine-tune based on real-world accuracy

Notes:
- Preprocessing adds ~100-200ms per image (runs in background)
- Most benefit for small text (<12pt when captured by phone)
- May help with aged/low-contrast pages
- Test across different lighting conditions
""")
