#!/usr/bin/swift
import Foundation
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins
#if os(macOS)
import AppKit
#else
import UIKit
#endif

// MARK: - Configurable Preprocessing

func preprocessLowResImage(
    _ cgImage: CGImage,
    scaleFactor: CGFloat = 2.5,
    contrast: CGFloat = 2.0,
    label: String
) -> CGImage? {
    let ciImage = CIImage(cgImage: cgImage)

    // 1. Upscale using Lanczos
    guard let upscaleFilter = CIFilter(name: "CILanczosScaleTransform") else {
        return nil
    }
    upscaleFilter.setValue(ciImage, forKey: kCIInputImageKey)
    upscaleFilter.setValue(scaleFactor, forKey: kCIInputScaleKey)
    upscaleFilter.setValue(1.0, forKey: kCIInputAspectRatioKey)

    guard let upscaledImage = upscaleFilter.outputImage else { return nil }

    // 2. Apply contrast and desaturation
    let contrastFilter = CIFilter.colorControls()
    contrastFilter.inputImage = upscaledImage
    contrastFilter.contrast = Float(contrast)
    contrastFilter.saturation = 0.0

    guard let highContrastImage = contrastFilter.outputImage else { return nil }

    // 3. Render back to CGImage
    let context = CIContext(options: [.useSoftwareRenderer: false])
    guard let result = context.createCGImage(highContrastImage, from: highContrastImage.extent) else {
        return nil
    }

    print("  [\(label)] Scale: \(scaleFactor)x, Contrast: \(contrast)")
    return result
}

// MARK: - OCR Function

func runOCR(cgImage: CGImage, label: String) -> [String] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
    request.usesLanguageCorrection = false
    request.minimumTextHeight = 0.0

    let handler = VNImageRequestHandler(cgImage: cgImage, orientation: .up, options: [:])

    do {
        try handler.perform([request])
    } catch {
        print("  ❌ OCR error: \(error)")
        return []
    }

    guard let results = request.results else {
        return []
    }

    var lines: [String] = []
    for obs in results {
        if let candidate = obs.topCandidates(1).first {
            lines.append(candidate.string)
        }
    }

    print("  📊 Recognized \(lines.count) lines")
    if !lines.isEmpty {
        lines.prefix(3).forEach { print("     • \($0)") }
        if lines.count > 3 {
            print("     ... and \(lines.count - 3) more")
        }
    }

    return lines
}

// MARK: - Main

print("🔍 OCR Preprocessing Tuning Test")
print(String(repeating: "=", count: 60))

// Load test image
let testImagePath = "/Users/chester.kim/workspace/trashcan/orientalmeddic/data/test/IMG_1726.jpg"
guard let imageData = try? Data(contentsOf: URL(fileURLWithPath: testImagePath)) else {
    print("❌ Failed to load image")
    exit(1)
}

#if os(macOS)
guard let nsImage = NSImage(data: imageData),
      let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("❌ Failed to convert image")
    exit(1)
}
#else
guard let uiImage = UIImage(data: imageData),
      let cgImage = uiImage.cgImage else {
    print("❌ Failed to convert image")
    exit(1)
}
#endif

print("✅ Loaded image: \(cgImage.width)x\(cgImage.height)")
print()

// Test configurations
let configs: [(scale: CGFloat, contrast: CGFloat, name: String)] = [
    (1.0, 1.0, "Original (baseline)"),
    (2.0, 1.5, "Light preprocessing (2x + 1.5 contrast)"),
    (2.5, 2.0, "Medium preprocessing (2.5x + 2.0 contrast)"),
    (3.0, 2.0, "Aggressive upscale (3x + 2.0 contrast)"),
    (2.0, 2.5, "High contrast (2x + 2.5 contrast)"),
]

var results: [(name: String, count: Int)] = []

for (scale, contrast, name) in configs {
    print(String(repeating: "-", count: 60))
    print("TEST: \(name)")

    let processedImage: CGImage
    if scale == 1.0 && contrast == 1.0 {
        processedImage = cgImage
    } else {
        guard let preprocessed = preprocessLowResImage(cgImage, scaleFactor: scale, contrast: contrast, label: name) else {
            print("  ❌ Preprocessing failed")
            continue
        }
        processedImage = preprocessed
    }

    let lines = runOCR(cgImage: processedImage, label: name)
    results.append((name, lines.count))
}

// Summary
print()
print(String(repeating: "=", count: 60))
print("📊 SUMMARY")
print(String(repeating: "=", count: 60))

let baselineCount = results[0].count
for (name, count) in results {
    let delta = count - baselineCount
    let symbol = delta > 0 ? "✅" : (delta < 0 ? "❌" : "→")
    let sign = delta > 0 ? "+" : ""
    print("\(symbol) \(name): \(count) lines (\(sign)\(delta))")
}

print()
print("💡 Recommendations:")
print("  • Try the config that gives the highest line count")
print("  • Then test with other test images (IMG_1727, IMG_1728, etc.)")
print("  • Fine-tune from there (±0.5 on scale, ±0.2 on contrast)")
