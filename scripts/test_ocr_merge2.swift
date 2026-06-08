#!/usr/bin/env swift
// test_ocr_merge2.swift — 두 패스 글자별 bbox 병합 v2
// 전략: zh에서 한자만 신뢰, ko에서 한글만 신뢰, 위치로 합침
//
// Usage: swift test_ocr_merge2.swift <이미지 경로>

import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    print("Usage: swift test_ocr_merge2.swift <이미지 경로>")
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

func isLatin(_ ch: Character) -> Bool {
    let v = ch.unicodeScalars.first?.value ?? 0
    return (0x0041...0x005A).contains(v) || (0x0061...0x007A).contains(v)
}

func isDigit(_ ch: Character) -> Bool {
    let v = ch.unicodeScalars.first?.value ?? 0
    return (0x0030...0x0039).contains(v)
}

struct CharBox {
    let char: Character
    let box: CGRect
    let source: String  // "zh" or "ko"
}

// MARK: - 글자별 bbox 추출

func extractCharBoxes(cgImage: CGImage, languages: [String]) -> [CharBox] {
    var charBoxes: [CharBox] = []
    let src = languages[0].hasPrefix("zh") ? "zh" : "ko"

    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let str = candidate.string
            for idx in str.indices {
                let range = idx..<str.index(after: idx)
                if let charBox = try? candidate.boundingBox(for: range) {
                    charBoxes.append(CharBox(char: str[idx], box: charBox.boundingBox, source: src))
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
let zhAll = extractCharBoxes(cgImage: cgImage, languages: ["zh-Hant", "zh-Hans"])

print("Pass 2: ko OCR...")
let koAll = extractCharBoxes(cgImage: cgImage, languages: ["ko-KR"])

// zh에서 한자 + 기호/숫자/라틴만 추출
let zhTrusted = zhAll.filter { isHanja($0.char) || $0.char == "." || $0.char == "," || $0.char == "(" || $0.char == ")" || $0.char == "。" || $0.char == "，" || isLatin($0.char) || isDigit($0.char) || $0.char == "-" || $0.char == " " || $0.char == "•" || $0.char == "?" || $0.char == "=" || $0.char == "|" || $0.char == "（" || $0.char == "）" }

// ko에서 한글만 추출
let koTrusted = koAll.filter { isHangul($0.char) }

print("zh trusted: \(zhTrusted.count)글자 (한자+기호)")
print("ko trusted: \(koTrusted.count)글자 (한글)")

// zh에서 한자는 무조건 유지, 한자가 아닌 것만 ko로 교체
var combined: [CharBox] = []

// 간체자 필터: 한국 문서에서 간체자는 나올 수 없음 -> 한글을 잘못 읽은 것
let simplifiedChars: Set<Character> = [
    "\u{53f6}", // 叶 (= 葉)
    "\u{5907}", // 备 (= 備)
    "\u{8865}", // 补 (= 補)
    "\u{6765}", // 来 (= 來)
    "\u{5bf9}", // 对 (= 對)
    "\u{4e22}", // 丢 (= 丟)
    "\u{4e2a}", // 个 (= 個)
    "\u{5356}", // 卖 (= 賣)
    "\u{53cc}", // 双 (= 雙)
    "\u{5170}", // 兰 (= 蘭)
    "\u{522b}", // 别
    "\u{53eb}", // 叫
    "\u{4e27}", // 丧 (= 喪)
    "\u{4ea1}", // 亡
    "\u{5f53}", // 当 (= 當)
    "\u{8d5e}", // 赞 (= 贊)
    "\u{5316}", // 化
    "\u{5de5}", // 工
    "\u{5386}", // 历 (= 歷)
    "\u{4e1c}", // 东 (= 東)
    "\u{5e01}", // 币 (= 幣)
    "\u{53f7}", // 号 (= 號)
    "\u{4e0e}", // 与 (= 與)
    "\u{8ba1}", // 计 (= 計)
    "\u{5206}", // 分
    "\u{4e60}", // 习 (= 習)
    "\u{8fdb}", // 进 (= 進)
    "\u{8d44}", // 资 (= 資)
    "\u{90ae}", // 邮
    "\u{9879}", // 项 (= 項)
    "\u{5151}", // 兑
    "\u{6bd5}", // 毕
    "\u{5c14}", // 尔 (= 爾)
    "\u{4e3d}", // 丽 (= 麗)
    "\u{4e30}", // 丰 (= 豐)
    "\u{4e3a}", // 为 (= 為)
    "\u{65f6}", // 时 (= 時)
    "\u{4e66}", // 书 (= 書)
    "\u{5e76}", // 并 (= 並)
    "\u{4ece}", // 从 (= 從)
    "\u{4e0d}", // 不 - 이건 번체에도 있음, 제외
    "\u{6c14}", // 气 (= 氣)
    "\u{4e50}", // 乐 (= 樂)
    "\u{8fc7}", // 过 (= 過)
    "\u{8fd0}", // 运 (= 運)
    "\u{8fbe}", // 达 (= 達)
    "\u{8d39}", // 费 (= 費)
    "\u{8d22}", // 财 (= 財)
    "\u{6c42}", // 求
    "\u{7ed3}", // 结 (= 結)
    "\u{6548}", // 效
    "\u{89c4}", // 规 (= 規)
    "\u{521b}", // 创 (= 創)
    "\u{89e3}", // 解
    "\u{6570}", // 数 (= 數)
    "\u{7ba1}", // 管
    "\u{6b22}", // 欢 (= 歡)
    "\u{5e94}", // 应 (= 應)
    "\u{58c1}", // 壁
    "\u{9f20}", // 鼠
    "\u{5561}", // 啡
    "\u{6d8c}", // 涌
    "\u{62ff}", // 拿
    "\u{5ba2}", // 客
    "\u{6c5f}", // 江
    "\u{5203}", // 刃
    "\u{54e5}", // 哥
    "\u{6597}", // 斗
    "\u{9e1f}", // 鸟 (= 鳥)
    "\u{5c71}", // 山
    "\u{5ddd}", // 川
    "\u{5bfb}", // 寻 (= 尋)
]

func isSimplified(_ ch: Character) -> Bool {
    return simplifiedChars.contains(ch)
}

// zh에서 한자는 무조건 유지 (단, 간체자 제외)
let zhHanja = zhTrusted.filter { isHanja($0.char) && !isSimplified($0.char) }
combined += zhHanja

// 2) zh에서 한자가 아닌 글자(기호/숫자/영어) 중, ko 한글과 겹치지 않는 것만 추가
let zhNonHanja = zhTrusted.filter { !isHanja($0.char) }
for zh in zhNonHanja {
    let hasKoOverlap = koTrusted.contains { ko in
        let overlapX = max(0, min(zh.box.maxX, ko.box.maxX) - max(zh.box.minX, ko.box.minX))
        let overlapY = max(0, min(zh.box.maxY, ko.box.maxY) - max(zh.box.minY, ko.box.minY))
        let overlapArea = overlapX * overlapY
        let zhArea = zh.box.width * zh.box.height
        return zhArea > 0 && overlapArea / zhArea > 0.3
    }
    if !hasKoOverlap {
        combined.append(zh)
    }
}

// 3) ko 한글 중, zh 한자와 겹치지 않는 것만 추가
for ko in koTrusted {
    let hasHanjaOverlap = zhHanja.contains { zh in
        let overlapX = max(0, min(zh.box.maxX, ko.box.maxX) - max(zh.box.minX, ko.box.minX))
        let overlapY = max(0, min(zh.box.maxY, ko.box.maxY) - max(zh.box.minY, ko.box.minY))
        let overlapArea = overlapX * overlapY
        let koArea = ko.box.width * ko.box.height
        return koArea > 0 && overlapArea / koArea > 0.3
    }
    if !hasHanjaOverlap {
        combined.append(ko)
    }
}

let lines = groupByLine(combined)

print("\n=== 병합 결과 (\(lines.count)줄) ===")
for line in lines {
    let text = String(line.map { $0.char })
    print("  \(text)")
}
