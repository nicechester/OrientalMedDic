#!/usr/bin/swift
import Foundation
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins
#if os(macOS)
import AppKit
typealias PlatformImage = NSImage
#else
import UIKit
typealias PlatformImage = UIImage
#endif

// MARK: - Preprocessing Function

func preprocessLowResImage(_ cgImage: CGImage) -> CGImage? {
    let ciImage = CIImage(cgImage: cgImage)

    // 1. Upscale using Lanczos (2.5x for good quality/performance trade-off)
    let scaleFactor: CGFloat = 2.5
    guard let upscaleFilter = CIFilter(name: "CILanczosScaleTransform") else {
        print("❌ Failed to create upscale filter")
        return nil
    }
    upscaleFilter.setValue(ciImage, forKey: kCIInputImageKey)
    upscaleFilter.setValue(scaleFactor, forKey: kCIInputScaleKey)
    upscaleFilter.setValue(1.0, forKey: kCIInputAspectRatioKey)

    guard let upscaledImage = upscaleFilter.outputImage else {
        print("❌ Failed to upscale image")
        return nil
    }

    // 2. Boost contrast and convert to grayscale
    let contrastFilter = CIFilter.colorControls()
    contrastFilter.inputImage = upscaledImage
    contrastFilter.contrast = 2.0      // Sharpen edges
    contrastFilter.saturation = 0.0    // Remove color noise

    guard let highContrastImage = contrastFilter.outputImage else {
        print("❌ Failed to apply contrast filter")
        return nil
    }

    // 3. Render back to CGImage
    let context = CIContext(options: [.useSoftwareRenderer: false])
    guard let result = context.createCGImage(highContrastImage, from: highContrastImage.extent) else {
        print("❌ Failed to render CGImage")
        return nil
    }

    return result
}

// MARK: - OCR Function

func runOCR(cgImage: CGImage, label: String) -> [String] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
    request.usesLanguageCorrection = false
    request.minimumTextHeight = 0.0  // Don't filter small text

    let handler = VNImageRequestHandler(cgImage: cgImage, orientation: .up, options: [:])

    do {
        try handler.perform([request])
    } catch {
        print("❌ OCR error: \(error)")
        return []
    }

    guard let results = request.results else {
        print("❌ No OCR results for \(label)")
        return []
    }

    var lines: [String] = []
    for obs in results {
        if let candidate = obs.topCandidates(1).first {
            lines.append(candidate.string)
        }
    }

    print("\n📄 \(label) - Recognized \(lines.count) lines:")
    lines.forEach { print("  • \($0)") }

    return lines
}

// MARK: - Main

print("🔍 Testing OCR Preprocessing Pipeline")
print(String(repeating: "=", count: 50))

// Load test image
let testImagePath = "/Users/chester.kim/workspace/trashcan/orientalmeddic/data/test/IMG_1726.jpg"
guard let imageData = try? Data(contentsOf: URL(fileURLWithPath: testImagePath)) else {
    print("❌ Failed to load image data from \(testImagePath)")
    exit(1)
}

#if os(macOS)
guard let nsImage = NSImage(data: imageData),
      let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("❌ Failed to convert NSImage to CGImage")
    exit(1)
}
#else
guard let uiImage = UIImage(data: imageData),
      let cgImage = uiImage.cgImage else {
    print("❌ Failed to convert UIImage to CGImage")
    exit(1)
}
#endif

print("✅ Loaded image: \(testImagePath)")
print("   Size: \(cgImage.width)x\(cgImage.height)")

// Test 1: Original image
print("\n" + String(repeating: "-", count: 50))
print("TEST 1: ORIGINAL IMAGE (no preprocessing)")
print(String(repeating: "-", count: 50))
let originalResults = runOCR(cgImage: cgImage, label: "Original")

// Test 2: Preprocessed image
print("\n" + String(repeating: "-", count: 50))
print("TEST 2: PREPROCESSED IMAGE (upscale + contrast boost)")
print(String(repeating: "-", count: 50))
print("Preprocessing... (Lanczos 2.5x upscale + contrast boost)")

guard let preprocessedCGImage = preprocessLowResImage(cgImage) else {
    print("❌ Preprocessing failed")
    exit(1)
}

print("✅ Preprocessing complete")
print("   Preprocessed size: \(preprocessedCGImage.width)x\(preprocessedCGImage.height)")

let preprocessedResults = runOCR(cgImage: preprocessedCGImage, label: "Preprocessed")

// Summary
print("\n" + String(repeating: "=", count: 50))
print("📊 COMPARISON")
print(String(repeating: "=", count: 50))
print("Original: \(originalResults.count) lines recognized")
print("Preprocessed: \(preprocessedResults.count) lines recognized")

if preprocessedResults.count > originalResults.count {
    let improvement = ((Double(preprocessedResults.count) - Double(originalResults.count)) / Double(originalResults.count)) * 100
    print("✅ Improvement: +\(String(format: "%.1f", improvement))%")
} else if preprocessedResults.count == originalResults.count {
    print("→ Same result (no improvement, but no regression)")
} else {
    print("⚠️ Fewer results in preprocessed (may need tuning)")
}

print("\n💡 Tip: Check if the preprocessed version caught smaller hanja characters")
print("   that the original missed!")
