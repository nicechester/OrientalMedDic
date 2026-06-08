#!/usr/bin/env swift
// test_ocr.swift — macOS에서 이미지 파일로 투 패스 OCR 테스트
// 사용법: swift test_ocr.swift <이미지 경로>

import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    print("사용법: swift test_ocr.swift <이미지 경로>")
    exit(1)
}

let imagePath = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: imagePath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("이미지를 열 수 없습니다: \(imagePath)")
    exit(1)
}

func runOCR(cgImage: CGImage, languages: [String], customWords: [String] = []) -> [(String, Float, CGRect)] {
    var results: [(String, Float, CGRect)] = []
    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            if let candidate = obs.topCandidates(1).first {
                results.append((candidate.string, candidate.confidence, obs.boundingBox))
            }
        }
    }
    request.recognitionLanguages = languages
    request.recognitionLevel = .accurate
    if !customWords.isEmpty {
        request.customWords = customWords
    }
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try? handler.perform([request])
    return results
}

func isHanja(_ ch: Character) -> Bool {
    let v = ch.unicodeScalars.first?.value ?? 0
    return (0x4E00...0x9FFF).contains(v) || (0x3400...0x4DBF).contains(v) || (0xF900...0xFAFF).contains(v)
}

func isHangul(_ ch: Character) -> Bool {
    let v = ch.unicodeScalars.first?.value ?? 0
    return (0xAC00...0xD7AF).contains(v) || (0x3131...0x318E).contains(v)
}

func computeIoU(_ a: CGRect, _ b: CGRect) -> CGFloat {
    let intersection = a.intersection(b)
    guard !intersection.isNull else { return 0 }
    let iArea = intersection.width * intersection.height
    let uArea = a.width * a.height + b.width * b.height - iArea
    return uArea > 0 ? iArea / uArea : 0
}

func combineKoZh(koText: String, zhText: String) -> String {
    let hanjaChars = Array(zhText.filter { isHanja($0) })
    guard !hanjaChars.isEmpty else { return koText }

    var result = ""
    var hanjaIdx = 0

    for ch in koText {
        if isHanja(ch) {
            result.append(ch)
            hanjaIdx += 1
        } else if isHangul(ch) || ch.isWhitespace || ch.isPunctuation {
            result.append(ch)
        } else {
            // 숫자/알파벳 등 의심스러운 문자 → 한자로 교체
            if hanjaIdx < hanjaChars.count {
                result.append(hanjaChars[hanjaIdx])
                hanjaIdx += 1
            } else {
                result.append(ch)
            }
        }
    }
    return result
}

// --- 실행 ---

print("=== Pass 1: 한글 우선 (ko-KR) ===")
let koResults = runOCR(cgImage: cgImage, languages: ["ko-KR"])
for (text, conf, _) in koResults {
    print("  [\(String(format: "%.2f", conf))] \(text)")
}

print("\n=== Pass 2: 한자 우선 (zh-Hant, zh-Hans) ===")
let zhResults = runOCR(cgImage: cgImage, languages: ["zh-Hant", "zh-Hans"])
for (text, conf, _) in zhResults {
    print("  [\(String(format: "%.2f", conf))] \(text)")
}

print("\n=== Pass 3: 혼합 (ko-KR + zh-Hant) ===")
let mixResults = runOCR(cgImage: cgImage, languages: ["ko-KR", "zh-Hant"])
for (text, conf, _) in mixResults {
    print("  [\(String(format: "%.2f", conf))] \(text)")
}

print("\n=== Pass 4: 혼합 역순 (zh-Hant + ko-KR) ===")
let mix2Results = runOCR(cgImage: cgImage, languages: ["zh-Hant", "ko-KR"])
for (text, conf, _) in mix2Results {
    print("  [\(String(format: "%.2f", conf))] \(text)")
}

// --- 언어 보정 OFF 테스트 ---

func runOCRNoCorrection(cgImage: CGImage, languages: [String]) -> [(String, Float, CGRect)] {
    var results: [(String, Float, CGRect)] = []
    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            if let candidate = obs.topCandidates(1).first {
                results.append((candidate.string, candidate.confidence, obs.boundingBox))
            }
        }
    }
    request.recognitionLanguages = languages
    request.usesLanguageCorrection = false
    request.recognitionLevel = .accurate
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try? handler.perform([request])
    return results
}

print("\n=== Pass 5: zh우선 + 보정OFF ===")
let zhNoCorrResults = runOCRNoCorrection(cgImage: cgImage, languages: ["zh-Hant", "zh-Hans", "ko-KR"])
for (text, conf, _) in zhNoCorrResults {
    print("  [\(String(format: "%.2f", conf))] \(text)")
}

print("\n=== Pass 6: ko우선 + 보정OFF ===")
let koNoCorrResults = runOCRNoCorrection(cgImage: cgImage, languages: ["ko-KR", "zh-Hant", "zh-Hans"])
for (text, conf, _) in koNoCorrResults {
    print("  [\(String(format: "%.2f", conf))] \(text)")
}

print("\n=== 병합 결과 (기존 로직) ===")
var merged: [(CGRect, String)] = []
for (koText, _, koBox) in koResults {
    var bestZhText: String?
    var bestIoU: CGFloat = 0
    for (zhText, _, zhBox) in zhResults {
        let iou = computeIoU(koBox, zhBox)
        if iou > bestIoU {
            bestIoU = iou
            bestZhText = zhText
        }
    }
    if let zhText = bestZhText, bestIoU > 0.3 {
        let combined = combineKoZh(koText: koText, zhText: zhText)
        merged.append((koBox, combined))
    } else {
        merged.append((koBox, koText))
    }
}
merged.sort { $0.0.origin.y > $1.0.origin.y }

for (_, text) in merged {
    print("  \(text)")
}

// --- Pass 7: 한자 우선 + customWords 한글 토씨 ---

let koreanParticles: [String] = [
    // 조사
    "은", "는", "이", "가", "을", "를", "의", "에", "에서", "로", "으로",
    "도", "만", "부터", "까지", "보다", "과", "와", "라", "나",
    // 어미/접속
    "하고", "하여", "하여는", "으로서", "로서",
    "한", "할", "하는", "하다", "있다", "없다",
    "된", "되는", "되어",
    "적", "적으로", "적인",
    // 일반 어휘
    "그", "또는", "또한", "및", "등",
    "수가", "것이다", "들어",
    "있는", "없는", "있을", "없을",
    // 예문 특정 단어
    "나아가서", "너무도", "적다고",
    "함으로써", "가져올", "주는",
    "여기서", "그러나", "또한",
    "이르는", "이룩할",
]

print("\n=== Pass 7: zh우선 + customWords(한글토씨) ===")
let customResults = runOCR(cgImage: cgImage, languages: ["zh-Hant", "zh-Hans", "ko-KR"], customWords: koreanParticles)
for (text, conf, _) in customResults {
    print("  [\(String(format: "%.2f", conf))] \(text)")
}

// --- Pass 8: 글자별 bounding box 기반 병합 ---

func runOCRWithCharBoxes(cgImage: CGImage, languages: [String]) -> [(Character, CGRect)] {
    var charResults: [(Character, CGRect)] = []
    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let fullString = candidate.string
            for index in fullString.indices {
                let range = index..<fullString.index(after: index)
                if let charBox = try? candidate.boundingBox(for: range) {
                    let char = fullString[index]
                    charResults.append((char, charBox.boundingBox))
                }
            }
        }
    }
    request.recognitionLanguages = languages
    request.recognitionLevel = .accurate
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try? handler.perform([request])
    return charResults
}

print("\n=== Pass 8: 글자별 병합 (zh결과에서 한자, ko결과에서 한글) ===")

let zhChars = runOCRWithCharBoxes(cgImage: cgImage, languages: ["zh-Hant", "zh-Hans"])
let koChars = runOCRWithCharBoxes(cgImage: cgImage, languages: ["ko-KR"])

// zh 결과를 기준으로, 각 글자가 한자면 그대로 쓰고
// 한자가 아니면 같은 위치의 ko 결과에서 가져옴
func centerOf(_ rect: CGRect) -> CGPoint {
    CGPoint(x: rect.midX, y: rect.midY)
}

func distance(_ a: CGPoint, _ b: CGPoint) -> CGFloat {
    sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))
}

// 줄 단위로 그룹핑 (y좌표 기준)
func groupByLine(_ chars: [(Character, CGRect)]) -> [[(Character, CGRect)]] {
    guard !chars.isEmpty else { return [] }
    let sorted = chars.sorted { $0.1.origin.y > $1.1.origin.y }
    var lines: [[(Character, CGRect)]] = [[sorted[0]]]
    for i in 1..<sorted.count {
        let prevY = lines.last!.last!.1.origin.y
        let currY = sorted[i].1.origin.y
        if abs(currY - prevY) < 0.01 { // 같은 줄
            lines[lines.count - 1].append(sorted[i])
        } else {
            lines.append([sorted[i]])
        }
    }
    // 각 줄 내에서 x좌표로 정렬
    return lines.map { $0.sorted { $0.1.origin.x < $1.1.origin.x } }
}

let zhLines = groupByLine(zhChars)
let koLines = groupByLine(koChars)

// 줄 매칭: y좌표가 가장 가까운 ko줄 찾기
func findMatchingKoLine(zhLineY: CGFloat) -> [(Character, CGRect)]? {
    var best: [(Character, CGRect)]?
    var bestDist: CGFloat = .greatestFiniteMagnitude
    for koLine in koLines {
        let koY = koLine.first!.1.origin.y
        let dist = abs(koY - zhLineY)
        if dist < bestDist {
            bestDist = dist
            best = koLine
        }
    }
    return bestDist < 0.02 ? best : nil
}

for zhLine in zhLines {
    let zhLineY = zhLine.first!.1.origin.y
    let koLine = findMatchingKoLine(zhLineY: zhLineY)
    
    var resultLine = ""
    for (zhChar, zhBox) in zhLine {
        if isHanja(zhChar) {
            // 한자면 zh 결과 사용
            resultLine += String(zhChar)
        } else if let koLine = koLine {
            // 한자가 아니면 같은 x위치의 ko 글자 찾기
            let zhCenter = centerOf(zhBox)
            var bestKoChar: Character = zhChar
            var bestDist: CGFloat = .greatestFiniteMagnitude
            for (koChar, koBox) in koLine {
                let dist = distance(zhCenter, centerOf(koBox))
                if dist < bestDist {
                    bestDist = dist
                    bestKoChar = koChar
                }
            }
            // 가까운 ko 글자가 한글이면 사용, 아니면 zh 그대로
            if isHangul(bestKoChar) {
                resultLine += String(bestKoChar)
            } else {
                resultLine += String(zhChar)
            }
        } else {
            resultLine += String(zhChar)
        }
    }
    print("  \(resultLine)")
}
