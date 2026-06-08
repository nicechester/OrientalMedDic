import Vision
import UIKit

/// 2-pass Vision OCR: 한국어 1차 → 괄호 내 한자 2차 중국어 인식
enum OCRService {

    struct OCRLine {
        let text: String
        let box: CGRect // normalized, Vision coordinate (bottom-left origin)
    }

    /// 이미지에서 2-pass OCR 수행, 결과를 줄 단위로 반환
    static func recognize(cgImage: CGImage) -> [OCRLine] {
        // Pass 1: 한국어+중국어 동시 인식 (기본 인식률 유지)
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
        request.usesLanguageCorrection = false

        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        try? handler.perform([request])
        guard let results = request.results else { return [] }

        var output: [OCRLine] = []

        for obs in results {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let text = candidate.string
            let lineBbox = obs.boundingBox

            // 괄호 없는 줄은 그대로 출력
            guard text.contains("(") || text.contains("\u{FF08}") else {
                output.append(OCRLine(text: text, box: lineBbox))
                continue
            }

            // 괄호 안 내용을 중국어 OCR로 재인식
            let finalText = resolveParentheses(text: text, candidate: candidate, cgImage: cgImage)
            output.append(OCRLine(text: finalText, box: lineBbox))
        }

        return output
    }

    /// 괄호 안 영역을 중국어 OCR로 재인식하여 치환
    private static func resolveParentheses(text: String, candidate: VNRecognizedText, cgImage: CGImage) -> String {
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
                        }
                    }
                }
            }

            finalText += "(\(replacement))"
            i = text.index(after: closeIdx)
        }

        return finalText
    }

    private static func isCJK(_ s: String) -> Bool {
        let trimmed = s.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return false }
        return trimmed.allSatisfy { c in
            let v = c.unicodeScalars.first!.value
            return (v >= 0x4E00 && v <= 0x9FFF) || (v >= 0x3400 && v <= 0x4DBF) || (v >= 0xF900 && v <= 0xFAFF)
        }
    }
}
