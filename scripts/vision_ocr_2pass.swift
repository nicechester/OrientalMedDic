#!/usr/bin/env swift
// vision_ocr_2pass.swift
// Usage: swift vision_ocr_2pass.swift <image_path>
// Output: JSON lines with {text, bbox} for fully clean lines (all parens resolved to CJK)

import Vision
import AppKit
import Foundation

guard CommandLine.arguments.count > 1 else {
    print("Usage: swift vision_ocr_2pass.swift <image_path>")
    exit(1)
}

let imgPath = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: imgPath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("ERROR: Failed to load image: \(imgPath)")
    exit(1)
}

func isCJK(_ s: String) -> Bool {
    let trimmed = s.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !trimmed.isEmpty else { return false }
    return trimmed.allSatisfy { c in
        let v = c.unicodeScalars.first!.value
        return (v >= 0x4E00 && v <= 0x9FFF) || (v >= 0x3400 && v <= 0x4DBF) || (v >= 0xF900 && v <= 0xFAFF)
    }
}

// Pass 1: Korean OCR
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["ko"]
request.usesLanguageCorrection = false

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try! handler.perform([request])
guard let results = request.results else { exit(0) }

struct LineResult: Codable {
    let text: String
    let bbox: [Double] // [x, y, width, height] normalized, bottom-left origin
}

var output: [LineResult] = []

for obs in results {
    guard let candidate = obs.topCandidates(1).first else { continue }
    let text = candidate.string
    
    // Get line bounding box
    let lineBbox = obs.boundingBox
    
    // Skip lines without parentheses - just output as-is
    guard text.contains("(") || text.contains("\u{FF08}") else {
        output.append(LineResult(
            text: text,
            bbox: [lineBbox.minX, lineBbox.minY, lineBbox.width, lineBbox.height]
        ))
        continue
    }
    
    // Process parenthesized content
    var finalText = ""
    var i = text.startIndex

    
    while i < text.endIndex {
        guard let openIdx = text[i...].firstIndex(where: { $0 == "(" || $0 == "\u{FF08}" }) else {
            finalText += String(text[i...])
            break
        }
        finalText += String(text[i..<openIdx])
        
        let closeChars: [Character] = [")", "\u{FF09}"]
        guard let closeIdx = text[text.index(after: openIdx)...].firstIndex(where: { closeChars.contains($0) }) else {
            finalText += String(text[openIdx...])
            break
        }
        
        let innerStart = text.index(after: openIdx)
        let innerText = String(text[innerStart..<closeIdx])
        
        var replacement = innerText
        var thisSuccess = false
        
        if innerStart < closeIdx {
            let innerRange = innerStart..<closeIdx
            if let box = try? candidate.boundingBox(for: innerRange)?.boundingBox {
                let padX: CGFloat = 0.012
                let padY: CGFloat = 0.006
                
                let expanded = CGRect(
                    x: max(0, box.minX - padX),
                    y: max(0, box.minY - padY),
                    width: min(1 - max(0, box.minX - padX), box.width + padX * 2),
                    height: min(1 - max(0, box.minY - padY), box.height + padY * 2)
                )
                
                let req2 = VNRecognizeTextRequest()
                req2.recognitionLevel = .accurate
                req2.recognitionLanguages = ["zh-Hant", "zh-Hans"]
                req2.usesLanguageCorrection = false
                req2.regionOfInterest = expanded
                
                let h2 = VNImageRequestHandler(cgImage: cgImage, options: [:])
                try? h2.perform([req2])
                
                if let zhText = req2.results?.first?.topCandidates(1).first?.string {
                    let cleaned = zhText.trimmingCharacters(in: CharacterSet(charactersIn: "\u{FF08}\u{FF09}()\u{300C}\u{300D} "))
                    if isCJK(cleaned) {
                        replacement = cleaned
                        thisSuccess = true
                    }
                }
            }
        }
        

        finalText += "(\(replacement))"
        i = text.index(after: closeIdx)
    }
    
    output.append(LineResult(
        text: finalText,
        bbox: [lineBbox.minX, lineBbox.minY, lineBbox.width, lineBbox.height]
    ))
}

// Output as JSON
let encoder = JSONEncoder()
let data = try! encoder.encode(output)
print(String(data: data, encoding: .utf8)!)
