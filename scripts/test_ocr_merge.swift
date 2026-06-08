#!/usr/bin/env swift
// test_ocr_merge.swift — 두 패스 글자별 bbox 병합 OCR
// 1. zh-Hant 우선 → 글자별 bbox
// 2. ko 우선 → 글자별 bbox
// 3. 같은 위치 글자끼리: 한자면 zh, 한글이면 ko 선택
//
// Usage: swift test_ocr_merge.swift <이미지 경로>

import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    print("Usage: swift test_ocr_merge.swift <이미지 경로>")
    exit(1)
}

let imagePath = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: imagePath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("이미지를 열 수 없습니다: \(imagePath)")
    exit(1)
}

// MARK: - 유틸

func isHanja(_ ch: Character) -> Bool {
    let v = ch.unicodeScalars.first?.value ?? 0
    return (0x4E00...0x9FFF).contains(v) || (0x3400...0x4DBF).contains(v) || (0xF900...0xFAFF).contains(v)
}

func isHangul(_ ch: Character) -> Bool {
    let v = ch.unicodeScalars.first?.value ?? 0
    return (0xAC00...0xD7AF).contains(v) || (0x3131...0x318E).contains(v)
}

struct CharBox {
    let char: Character
    let box: CGRect  // normalized (0~1, origin bottom-left)
}

// MARK: - 글자별 bbox 추출

func extractCharBoxes(cgImage: CGImage, languages: [String]) -> [CharBox] {
    var charBoxes: [CharBox] = []

    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let str = candidate.string
            for idx in str.indices {
                let range = idx..<str.index(after: idx)
                if let charBox = try? candidate.boundingBox(for: range) {
                    let char = str[idx]
                    charBoxes.append(CharBox(char: char, box: charBox.boundingBox))
                }
            }
        }
    }
    request.recognitionLanguages = languages
    request.recognitionLevel = .accurate

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try? handler.perform([request])
    return charBoxes
}

// MARK: - 줄 그룹핑 (y좌표 기준)

func groupByLine(_ chars: [CharBox]) -> [[CharBox]] {
    guard !chars.isEmpty else { return [] }
    // y 내림차순 정렬 (Vision 좌표: 아래가 0, 위가 1)
    let sorted = chars.sorted { $0.box.midY > $1.box.midY }

    // 평균 글자 높이 계산
    let avgHeight = sorted.map { $0.box.height }.reduce(0, +) / CGFloat(sorted.count)
    let threshold = max(avgHeight * 0.6, 0.008)

    var lines: [[CharBox]] = [[sorted[0]]]
    for i in 1..<sorted.count {
        let prevMidY = lines.last!.first!.box.midY  // 줄의 첫 글자 기준
        let currMidY = sorted[i].box.midY
        if abs(currMidY - prevMidY) < threshold {
            lines[lines.count - 1].append(sorted[i])
        } else {
            lines.append([sorted[i]])
        }
    }
    // 각 줄 내에서 x좌표 오름차순 정렬, 1글자짜리 줄 제거
    return lines.filter { $0.count > 1 }.map { $0.sorted { $0.box.minX < $1.box.minX } }
}

// MARK: - 병합
// 전략: zh 줄을 기준으로 순회하되, 각 글자 위치에서
// ko 결과에 한글이 있으면 한글 우선, 없으면 zh 사용

func mergeLines(zhLines: [[CharBox]], koLines: [[CharBox]]) -> [String] {
    var results: [String] = []

    for zhLine in zhLines {
        guard !zhLine.isEmpty else { continue }
        let zhMidY = zhLine.first!.box.midY
        let avgHeight = zhLine.map { $0.box.height }.reduce(0, +) / CGFloat(zhLine.count)

        // 매칭되는 ko 줄 찾기
        var bestKoLine: [CharBox]?
        var bestDist: CGFloat = .greatestFiniteMagnitude
        for koLine in koLines {
            guard let first = koLine.first else { continue }
            let lineMidY = koLine.map { $0.box.midY }.reduce(0, +) / CGFloat(koLine.count)
            let dist = abs(lineMidY - zhMidY)
            if dist < bestDist {
                bestDist = dist
                bestKoLine = koLine
            }
        }

        let koLine = (bestDist < avgHeight) ? bestKoLine : nil

        var merged = ""
        for zhChar in zhLine {
            // ko 결과에서 같은 위치에 한글이 있는지 확인
            if let koLine = koLine {
                let zhMidX = zhChar.box.midX
                let charWidth = zhChar.box.width

                // 이 위치에 겹치는 ko 글자 찾기
                var bestKoChar: CharBox?
                var bestOverlap: CGFloat = 0
                for koChar in koLine {
                    // x축 overlap 계산
                    let overlapStart = max(zhChar.box.minX, koChar.box.minX)
                    let overlapEnd = min(zhChar.box.maxX, koChar.box.maxX)
                    let overlap = max(0, overlapEnd - overlapStart)
                    if overlap > bestOverlap {
                        bestOverlap = overlap
                        bestKoChar = koChar
                    }
                }

                // ko에 한글이 있으면 한글 우선
                if let koChar = bestKoChar, bestOverlap > charWidth * 0.3, isHangul(koChar.char) {
                    merged += String(koChar.char)
                } else {
                    // ko에 한글 없으면 zh 사용 (한자든 뭐든)
                    merged += String(zhChar.char)
                }
            } else {
                merged += String(zhChar.char)
            }
        }
        results.append(merged)
    }
    return results
}

// MARK: - 실행

print("=== Pass 1: zh-Hant 우선 (글자별 bbox) ===")
let zhChars = extractCharBoxes(cgImage: cgImage, languages: ["zh-Hant", "zh-Hans"])
let zhLines = groupByLine(zhChars)
print("  \(zhChars.count)글자, \(zhLines.count)줄")
for line in zhLines {
    let text = String(line.map { $0.char })
    print("  \(text)")
}

print("\n=== Pass 2: ko 우선 (글자별 bbox) ===")
let koChars = extractCharBoxes(cgImage: cgImage, languages: ["ko-KR"])
let koLines = groupByLine(koChars)
print("  \(koChars.count)글자, \(koLines.count)줄")
for line in koLines {
    let text = String(line.map { $0.char })
    print("  \(text)")
}

print("\n=== 병합 결과 ===")
let merged = mergeLines(zhLines: zhLines, koLines: koLines)
for line in merged {
    print("  \(line)")
}
