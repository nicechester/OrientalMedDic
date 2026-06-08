import SwiftUI

struct ScanResultView: View {
    let inputText: String
    @Environment(\.dismiss) private var dismiss
    @State private var selectedCharacter: String?

    private var readingCharacters: [(word: String, reading: String)] {
        var words: [(String, String)] = []
        let chars = Array(inputText)
        var i = 0

        while i < chars.count {
            let char = chars[i]
            let scalar = char.unicodeScalars.first?.value ?? 0
            let isHanja = (scalar >= 0x4E00 && scalar <= 0x9FFF) || (scalar >= 0x3400 && scalar <= 0x4DBF)

            guard isHanja else { i += 1; continue }

            var endIdx = i
            while endIdx + 1 < chars.count {
                let nextChar = chars[endIdx + 1]
                let nextScalar = nextChar.unicodeScalars.first?.value ?? 0
                let nextIsHanja = (nextScalar >= 0x4E00 && nextScalar <= 0x9FFF) || (nextScalar >= 0x3400 && nextScalar <= 0x4DBF)
                guard nextIsHanja else { break }
                endIdx += 1
            }

            let word = String(chars[i...endIdx])

            // 먼저 정확한 단어 매칭을 확인
            let results = DictionaryDB.shared.lookup(text: word)
            let exactMatch = results.first { $0.term == word && $0.category != nil }

            let reading: String
            if let match = exactMatch {
                reading = match.reading
            } else {
                // 단어 매칭 실패 시 글자별 독음
                var charReading = ""
                for ch in word {
                    let r = DictionaryDB.shared.readingForChar(String(ch)) ?? "?"
                    charReading += r
                }
                reading = charReading
            }

            words.append((word, reading))
            i = endIdx + 1
        }

        return words
    }

    var body: some View {
        ZStack {
            VStack(spacing: 0) {
                HStack {
                    Text("독음")
                        .font(.headline)
                    Spacer()
                }
                .padding()

                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        GroupBox("원문 독음") {
                            if readingCharacters.isEmpty {
                                Text(DictionaryDB.shared.generateReadingText(for: inputText))
                                    .font(.title3)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            } else {
                                readingCharacterGrid()
                            }
                        }
                    }
                    .padding()
                }

                Divider()
                    .padding(.bottom, 60)
            }

            VStack {
                HStack {
                    Spacer()
                }
                Spacer()

                HStack(spacing: 40) {
                    Button(action: { dismiss() }) {
                        HStack(spacing: 6) {
                            Image(systemName: "xmark")
                            Text("취소")
                        }
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: 120)
                        .frame(height: 44)
                        .background(Color.gray.opacity(0.6))
                        .cornerRadius(8)
                    }
                }
                .padding()
                .padding(.bottom, 50)
            }
            .ignoresSafeArea(.keyboard)
        }
        .onChange(of: selectedCharacter) { _, character in
            if let char = character {
                dismiss()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                    NotificationCenter.default.post(name: NSNotification.Name("SearchWord"), object: nil, userInfo: ["word": char])
                }
                selectedCharacter = nil
            }
        }
    }

    private func readingCharacterGrid() -> some View {
        var rows: [[(String, String)]] = []
        var currentRow: [(String, String)] = []

        for (word, reading) in readingCharacters {
            currentRow.append((word, reading))
            if currentRow.count == 3 {
                rows.append(currentRow)
                currentRow = []
            }
        }
        if !currentRow.isEmpty {
            rows.append(currentRow)
        }

        return VStack(spacing: 8) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                HStack(spacing: 8) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, item in
                        let word = item.0
                        let reading = item.1
                        Button(action: { selectedCharacter = word }) {
                            VStack(spacing: 4) {
                                Text(word)
                                    .font(.headline)
                                    .foregroundStyle(.black)
                                Text(reading)
                                    .font(.subheadline)
                                    .foregroundStyle(.red)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(10)
                            .background(Color.gray.opacity(0.1))
                            .cornerRadius(6)
                        }
                    }
                    Spacer()
                }
            }
        }
    }
}
