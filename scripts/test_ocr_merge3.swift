#!/usr/bin/env swift
// test_ocr_merge3.swift — DB 기반 한자 검증 + 두 패스 병합
// 전략:
//   1. zh 우선 OCR → 글자별 bbox
//   2. 각 글자가 DB에 있는 한자면 → 진짜 한자
//   3. DB에 없으면 → 한글을 잘못 읽은 것 → ko 결과에서 한글 가져옴
//
// Usage: swift test_ocr_merge3.swift <이미지 경로>

import Foundation
import Vision
import AppKit
import SQLite3

guard CommandLine.arguments.count > 1 else {
    print("Usage: swift test_ocr_merge3.swift <이미지 경로>")
    exit(1)
}

let imagePath = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: imagePath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("이미지를 열 수 없습니다: \(imagePath)")
    exit(1)
}

// MARK: - DB 로드

let dbPath = (CommandLine.arguments.count > 2) ? CommandLine.arguments[2] : "data/hanjadic.db"
var db: OpaquePointer?
guard sqlite3_open_v2(dbPath, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
    print("DB 열기 실패: \(dbPath)")
    exit(1)
}

func isInDB(_ char: Character) -> Bool {
    let charStr = String(char)
    let sql = "SELECT 1 FROM hanja WHERE character = ? LIMIT 1"
    var stmt: OpaquePointer?
    defer { sqlite3_finalize(stmt) }
    guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else { return false }
    sqlite3_bind_text(stmt, 1, (charStr as NSString).utf8String, -1, nil)
    return sqlite3_step(stmt) == SQLITE_ROW
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
    let box: CGRect
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
                    charBoxes.append(CharBox(char: str[idx], box: charBox.boundingBox))
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

// MARK: - 줄 그룹핑

func groupByLine(_ chars: [CharBox]) -> [[CharBox]] {
    guard !chars.isEmpty else { return [] }
    let sorted = chars.sorted { $0.box.midY > $1.box.midY }
    let avgHeight = sorted.map { $0.box.height }.reduce(0, +) / CGFloat(sorted.count)
    let threshold = max(avgHeight * 0.6, 0.008)

    var lines: [[CharBox]] = [[sorted[0]]]
    for i in 1..<sorted.count {
        let prevMidY = lines.last!.first!.box.midY
        let currMidY = sorted[i].box.midY
        if abs(currMidY - prevMidY) < threshold {
            lines[lines.count - 1].append(sorted[i])
        } else {
            lines.append([sorted[i]])
        }
    }
    return lines.filter { $0.count > 1 }.map { $0.sorted { $0.box.minX < $1.box.minX } }
}

// MARK: - 실행

print("Pass 1: zh-Hant OCR...")
let zhChars = extractCharBoxes(cgImage: cgImage, languages: ["zh-Hant", "zh-Hans"])
print("  \(zhChars.count)글자")

// DB 검증: 한자 범위인데 DB에 없으면 가짜
var realHanjaCount = 0
var fakeHanjaCount = 0
for ch in zhChars {
    if isHanja(ch.char) {
        if isInDB(ch.char) { realHanjaCount += 1 }
        else { fakeHanjaCount += 1 }
    }
}
print("  진짜 한자(DB): \(realHanjaCount), 가짜 한자(DB에 없음): \(fakeHanjaCount)")

print("\nPass 2: ko OCR...")
let koChars = extractCharBoxes(cgImage: cgImage, languages: ["ko-KR"])
print("  \(koChars.count)글자")

// 병합: zh 줄 기준으로 순회
let zhLines = groupByLine(zhChars)
let koLines = groupByLine(koChars)

print("\n=== 병합 결과 (\(zhLines.count)줄) ===")

for zhLine in zhLines {
    guard !zhLine.isEmpty else { continue }
    let zhMidY = zhLine.first!.box.midY
    let avgHeight = zhLine.map { $0.box.height }.reduce(0, +) / CGFloat(zhLine.count)

    // 매칭되는 ko 줄 찾기
    var bestKoLine: [CharBox]?
    var bestDist: CGFloat = .greatestFiniteMagnitude
    for koLine in koLines {
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
        if isHanja(zhChar.char) && isInDB(zhChar.char) {
            // DB에 있는 한자 → 진짜 한자, 유지
            merged += String(zhChar.char)
        } else if isHanja(zhChar.char) && !isInDB(zhChar.char) {
            // DB에 없는 한자 → 한글을 잘못 읽은 것 → ko에서 가져옴
            if let koLine = koLine {
                let zhMidX = zhChar.box.midX
                var bestKo: CharBox?
                var bestOverlap: CGFloat = 0
                for ko in koLine {
                    let overlapX = max(0, min(zhChar.box.maxX, ko.box.maxX) - max(zhChar.box.minX, ko.box.minX))
                    let overlapY = max(0, min(zhChar.box.maxY, ko.box.maxY) - max(zhChar.box.minY, ko.box.minY))
                    let overlap = overlapX * overlapY
                    if overlap > bestOverlap {
                        bestOverlap = overlap
                        bestKo = ko
                    }
                }
                if let ko = bestKo, isHangul(ko.char) {
                    merged += String(ko.char)
                } else {
                    merged += String(zhChar.char)  // ko에도 없으면 그대로
                }
            } else {
                merged += String(zhChar.char)
            }
        } else {
            // 비한자 (기호, 숫자, 영어 등) → 그대로
            merged += String(zhChar.char)
        }
    }
    print("  \(merged)")
}

sqlite3_close(db)
