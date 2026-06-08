import Foundation
import SQLite3

class DictionaryDB {
    static let shared = DictionaryDB()

    private var db: OpaquePointer?
    private var readingCache: [String: String] = [:]

    private init() {
        openDatabase()
    }

    private func openDatabase() {
        guard let path = Bundle.main.path(forResource: "hanjadic", ofType: "db") else {
            print("[DictionaryDB] hanjadic.db 파일을 번들에서 찾을 수 없음")
            return
        }
        print("[DictionaryDB] DB 경로: \(path)")
        if sqlite3_open_v2(path, &db, SQLITE_OPEN_READONLY, nil) != SQLITE_OK {
            print("[DictionaryDB] DB 열기 실패")
        } else {
            print("[DictionaryDB] DB 열기 성공")
        }
    }

    func lookup(text: String) -> [DBResult] {
        guard db != nil else {
            print("DB 연결 없음")
            return []
        }
        var results: [DBResult] = []

        // 1. 단어 검색 먼저 (정확한 한글 독음을 얻기 위함)
        let herbalResults = lookupHerbal(text: text)
        let formulaResults = lookupFormula(text: text)
        let symptomResults = lookupSymptom(text: text)
        let acupointResults = lookupAcupoint(text: text)
        let hanjaWordResults = lookupHanjaWord(text: text)

        results += herbalResults
        results += formulaResults
        results += symptomResults
        results += acupointResults
        results += hanjaWordResults

        // 2. 단어 결과에서 정확한 한글 독음 추출
        var correctReading: [Character: String] = [:]
        for result in results {
            if !result.reading.isEmpty && result.category != nil {
                // 한글 독음을 글자별로 분해하여 저장
                var readings = result.reading.split(separator: " ").map(String.init)
                if readings.isEmpty {
                    readings = result.reading.split(separator: "-").map(String.init)
                }
                let hanjaChars = text.filter { char in
                    let scalar = char.unicodeScalars.first?.value ?? 0
                    return (scalar >= 0x4E00 && scalar <= 0x9FFF) || (scalar >= 0x3400 && scalar <= 0x4DBF)
                }
                var charIndex = 0
                for char in hanjaChars {
                    if charIndex < readings.count {
                        correctReading[char] = readings[charIndex]
                        charIndex += 1
                    }
                }
            }
        }

        // 3. 낱글자 검색 (정확한 독음 적용)
        results += lookupHanja(text: text, correctReadings: correctReading)

        // 정렬: 전체 매칭 > 한자어 > 다른 category(길이순) > 낱글자
        let categoryOrder: [String: Int] = [
            "한자어": 0,
            "본초": 1,
            "방제": 2,
            "경혈": 3,
            "증상": 4,
            "병명": 5
        ]

        return results.sorted { a, b in
            let aIsExactMatch = a.term == text
            let bIsExactMatch = b.term == text
            if aIsExactMatch != bIsExactMatch {
                return aIsExactMatch // 정확한 전체 매칭이 먼저
            }

            let aCategory = a.category
            let bCategory = b.category

            // category 있는 것이 category 없는 것보다 먼저
            if (aCategory != nil) != (bCategory != nil) {
                return aCategory != nil
            }

            // 같은 category 그룹 내에서 순서 정렬
            if aCategory != nil && bCategory != nil {
                let aOrder = categoryOrder[aCategory!] ?? 99
                let bOrder = categoryOrder[bCategory!] ?? 99
                if aOrder != bOrder {
                    return aOrder < bOrder
                }

                // 같은 category면 길이 순서 (긴 것부터)
                if a.term.count != b.term.count {
                    return a.term.count > b.term.count
                }
            }

            return false // 같으면 원래 순서 유지
        }
    }

    func lookupAllSubstrings(text: String) -> [DBResult] {
        guard db != nil else {
            print("DB 연결 없음")
            return []
        }
        let hanjaOnly = text.filter { char in
            let scalar = char.unicodeScalars.first?.value ?? 0
            return (scalar >= 0x4E00 && scalar <= 0x9FFF) || (scalar >= 0x3400 && scalar <= 0x4DBF)
        }

        var substrings = Set<String>()
        let indices = Array(hanjaOnly.indices)
        for start in indices.indices {
            for end in start..<indices.count {
                let substring = String(hanjaOnly[indices[start]...indices[end]])
                substrings.insert(substring)
            }
        }

        var allResults: [DBResult] = []
        var seenTerms = Set<String>()

        // 한글 검색 (증상명 등)
        let symptomResults = lookupSymptom(text: text)
        for result in symptomResults {
            if !seenTerms.contains(result.term) {
                seenTerms.insert(result.term)
                allResults.append(result)
            }
        }

        for substring in substrings {
            let results = lookup(text: substring)
            for result in results {
                if result.term == substring && !seenTerms.contains(result.term) {
                    seenTerms.insert(result.term)
                    allResults.append(result)
                }
            }

            let acupointResults = lookupAcupuncture(text: substring)
            for result in acupointResults {
                if result.term == substring && !seenTerms.contains(result.term) {
                    seenTerms.insert(result.term)
                    allResults.append(result)
                }
            }

            let diseaseResults = lookupDisease(text: substring)
            for result in diseaseResults {
                if result.term == substring && !seenTerms.contains(result.term) {
                    seenTerms.insert(result.term)
                    allResults.append(result)
                }
            }
        }

        // 정렬: 한자어 > 다른 category(길이순) > 낱글자
        let categoryOrder: [String: Int] = [
            "한자어": 0,
            "본초": 1,
            "방제": 2,
            "경혈": 3,
            "증상": 4,
            "병명": 5
        ]

        return allResults.sorted { a, b in
            let aCategory = a.category
            let bCategory = b.category

            // 1. category 있는 것이 먼저, 없는 것은 나중
            if (aCategory != nil) != (bCategory != nil) {
                return aCategory != nil
            }

            // 2. 같은 category 그룹 내에서 순서 정렬
            if aCategory != nil && bCategory != nil {
                let aOrder = categoryOrder[aCategory!] ?? 99
                let bOrder = categoryOrder[bCategory!] ?? 99
                if aOrder != bOrder {
                    return aOrder < bOrder
                }

                // 같은 category면 길이 순서 (긴 것부터)
                if a.term.count != b.term.count {
                    return a.term.count > b.term.count
                }
            }

            return false
        }
    }

    private func lookupAcupuncture(text: String) -> [DBResult] {
        var results: [DBResult] = []
        let sql = "SELECT name_hanja, name_korean, meridian, indication FROM acupuncture WHERE name_hanja = ? LIMIT 20"
        var stmt: OpaquePointer?

        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (text as NSString).utf8String, -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                let hanja = String(cString: sqlite3_column_text(stmt, 0))
                let korean = String(cString: sqlite3_column_text(stmt, 1))
                let meridian = sqlite3_column_text(stmt, 2).map { String(cString: $0) } ?? ""
                let indication = sqlite3_column_text(stmt, 3).map { String(cString: $0) } ?? ""

                results.append(DBResult(
                    term: hanja,
                    reading: korean,
                    category: "경혈",
                    description: "\(meridian) | \(indication)"
                ))
            }
        }
        sqlite3_finalize(stmt)
        return results
    }

    private func lookupDisease(text: String) -> [DBResult] {
        var results: [DBResult] = []
        let sql = "SELECT name_hanja, name_korean, symptoms FROM disease WHERE name_hanja = ? LIMIT 20"
        var stmt: OpaquePointer?

        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (text as NSString).utf8String, -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                let hanja = String(cString: sqlite3_column_text(stmt, 0))
                let korean = String(cString: sqlite3_column_text(stmt, 1))
                let symptoms = sqlite3_column_text(stmt, 2).map { String(cString: $0) } ?? ""

                results.append(DBResult(
                    term: hanja,
                    reading: korean,
                    category: "병명",
                    description: symptoms
                ))
            }
        }
        sqlite3_finalize(stmt)
        return results
    }

    private func lookupHanjaWord(text: String) -> [DBResult] {
        var results: [DBResult] = []
        let sql = "SELECT hanja, reading, meaning FROM hanja_word WHERE hanja = ?"
        var stmt: OpaquePointer?

        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (text as NSString).utf8String, -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                let hanja = String(cString: sqlite3_column_text(stmt, 0))
                let reading = String(cString: sqlite3_column_text(stmt, 1))
                let meaning = String(cString: sqlite3_column_text(stmt, 2))

                results.append(DBResult(
                    term: hanja,
                    reading: reading,
                    category: "한자어",
                    description: meaning
                ))
            }
        }
        sqlite3_finalize(stmt)
        return results
    }

    private func lookupHerbal(text: String) -> [DBResult] {
        var results: [DBResult] = []
        let sql = "SELECT name_hanja, name_korean, nature, flavor, meridian_tropism, efficacy FROM herbal WHERE name_hanja = ?"
        var stmt: OpaquePointer?

        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (text as NSString).utf8String, -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                let hanja = String(cString: sqlite3_column_text(stmt, 0))
                let korean = String(cString: sqlite3_column_text(stmt, 1))
                let nature = String(cString: sqlite3_column_text(stmt, 2))
                let flavor = String(cString: sqlite3_column_text(stmt, 3))
                let meridian = String(cString: sqlite3_column_text(stmt, 4))
                let efficacy = String(cString: sqlite3_column_text(stmt, 5))

                results.append(DBResult(
                    term: hanja,
                    reading: korean,
                    category: "본초",
                    description: "성미: \(nature)/\(flavor) | 귀경: \(meridian) | \(efficacy)"
                ))
            }
        }
        sqlite3_finalize(stmt)
        return results
    }

    private func lookupFormula(text: String) -> [DBResult] {
        var results: [DBResult] = []
        let sql = "SELECT name_hanja, name_korean, source_text, composition, indication FROM formula WHERE name_hanja = ?"
        var stmt: OpaquePointer?

        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (text as NSString).utf8String, -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                let hanja = String(cString: sqlite3_column_text(stmt, 0))
                let korean = String(cString: sqlite3_column_text(stmt, 1))
                let source = String(cString: sqlite3_column_text(stmt, 2))
                let comp = String(cString: sqlite3_column_text(stmt, 3))
                let indication = String(cString: sqlite3_column_text(stmt, 4))

                results.append(DBResult(
                    term: hanja,
                    reading: korean,
                    category: "방제",
                    description: "[\(source)] \(comp) | 주치: \(indication)"
                ))
            }
        }
        sqlite3_finalize(stmt)
        return results
    }

    private func lookupSymptom(text: String) -> [DBResult] {
        var results: [DBResult] = []

        // 한자 증상명으로만 검색 (정확한 매칭만)
        var symptomData: (hanja: String, korean: String, category: String)? = nil
        let sqlSymptom = "SELECT DISTINCT symptom_hanja, symptom_korean, category FROM symptom_formula WHERE symptom_hanja = ? LIMIT 1"
        var stmt: OpaquePointer?

        if sqlite3_prepare_v2(db, sqlSymptom, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (text as NSString).utf8String, -1, nil)
            if sqlite3_step(stmt) == SQLITE_ROW {
                let hanja = String(cString: sqlite3_column_text(stmt, 0))
                let korean = sqlite3_column_text(stmt, 1).map { String(cString: $0) } ?? ""
                let category = sqlite3_column_text(stmt, 2).map { String(cString: $0) } ?? ""
                symptomData = (hanja, korean, category)
            }
        }
        sqlite3_finalize(stmt)

        // 증상을 찾으면 관련 처방들 검색
        if let symptom = symptomData {
            var formulaList: [String] = []
            let sqlFormulas = "SELECT DISTINCT formula_hanja, formula_korean FROM symptom_formula WHERE symptom_hanja = ? ORDER BY formula_hanja"

            if sqlite3_prepare_v2(db, sqlFormulas, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (symptom.hanja as NSString).utf8String, -1, nil)
                while sqlite3_step(stmt) == SQLITE_ROW {
                    let formulaHanja = sqlite3_column_text(stmt, 0).map { String(cString: $0) } ?? ""
                    let formulaKorean = sqlite3_column_text(stmt, 1).map { String(cString: $0) } ?? ""

                    if !formulaHanja.isEmpty {
                        formulaList.append(formulaHanja)
                    } else if !formulaKorean.isEmpty {
                        formulaList.append(formulaKorean)
                    }
                }
            }
            sqlite3_finalize(stmt)

            if !formulaList.isEmpty {
                let description = "【증상의 처방】\n" + formulaList.prefix(10).joined(separator: ", ")
                + (formulaList.count > 10 ? " 외 \(formulaList.count - 10)개" : "")

                results.append(DBResult(
                    term: symptom.hanja,
                    reading: symptom.korean,
                    category: "증상",
                    description: description
                ))
            }
        }

        return results
    }

    private func lookupAcupoint(text: String) -> [DBResult] {
        var results: [DBResult] = []
        let sql = "SELECT name_hanja, name_korean, meridian, code, properties, indication FROM acupuncture WHERE category='혈위' AND name_hanja = ?"
        var stmt: OpaquePointer?

        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (text as NSString).utf8String, -1, nil)
            while sqlite3_step(stmt) == SQLITE_ROW {
                let hanja = String(cString: sqlite3_column_text(stmt, 0))
                let korean = String(cString: sqlite3_column_text(stmt, 1))
                let meridian = String(cString: sqlite3_column_text(stmt, 2))
                let code = String(cString: sqlite3_column_text(stmt, 3))
                let properties = String(cString: sqlite3_column_text(stmt, 4))
                let indication = String(cString: sqlite3_column_text(stmt, 5))

                results.append(DBResult(
                    term: hanja,
                    reading: "\(korean) (\(code))",
                    category: "경혈",
                    description: "\(meridian) | \(properties) | 주치: \(indication)"
                ))
            }
        }
        sqlite3_finalize(stmt)
        return results
    }

    private func lookupHanja(text: String) -> [DBResult] {
        return lookupHanja(text: text, correctReadings: [:])
    }

    private func lookupHanja(text: String, correctReadings: [Character: String]) -> [DBResult] {
        var results: [DBResult] = []
        // 공백/줄바꿈/숫자/구두점 제외, 한자만 필터
        let chars = text.filter { $0.unicodeScalars.first.map { $0.value >= 0x4E00 && $0.value <= 0x9FFF || $0.value >= 0x3400 && $0.value <= 0x4DBF } ?? false }

        var seen = Set<Character>()
        for char in chars {
            guard !seen.contains(char) else { continue }
            seen.insert(char)
            let charStr = String(char)
            let sql = "SELECT character, hangul_reading, korean_reading, definition_ko, definition FROM hanja WHERE character = ?"
            var stmt: OpaquePointer?

            if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (charStr as NSString).utf8String, -1, nil)
                if sqlite3_step(stmt) == SQLITE_ROW {
                    let character = String(cString: sqlite3_column_text(stmt, 0))
                    let hangulReading = sqlite3_column_text(stmt, 1).map { String(cString: $0) } ?? ""
                    let korean = sqlite3_column_text(stmt, 2).map { String(cString: $0) } ?? ""
                    let defKo = sqlite3_column_text(stmt, 3).map { String(cString: $0) } ?? ""
                    let defEn = sqlite3_column_text(stmt, 4).map { String(cString: $0) } ?? ""

                    // 정확한 독음이 있으면 그것을 사용, 없으면 기본음 사용
                    let reading = correctReadings[char] ?? (!hangulReading.isEmpty ? hangulReading : Self.romanToHangul(korean.lowercased()))
                    let description = !defKo.isEmpty ? defKo : defEn
                    if !reading.isEmpty {
                        results.append(DBResult(
                            term: character,
                            reading: reading,
                            category: nil,
                            description: description
                        ))
                    }
                }
            }
            sqlite3_finalize(stmt)
        }
        return results
    }

    // MARK: - 단어별 독음 생성
    /// 연속된 한자를 단어로 묶어 "독음(한자) 독음(한자) ..." 형식으로 반환
    func generateReadingText(for text: String) -> String {
        var result = ""
        var hanjaRun = ""

        for char in text {
            let scalar = char.unicodeScalars.first?.value ?? 0
            let isHanja = (scalar >= 0x4E00 && scalar <= 0x9FFF) || (scalar >= 0x3400 && scalar <= 0x4DBF)

            if isHanja {
                hanjaRun += String(char)
            } else {
                if !hanjaRun.isEmpty {
                    let reading = getReadingForHanja(hanjaRun)
                    result += "\(reading)(\(hanjaRun))"
                    hanjaRun = ""
                }
                result += String(char)
            }
        }
        if !hanjaRun.isEmpty {
            let reading = getReadingForHanja(hanjaRun)
            result += "\(reading)(\(hanjaRun))"
        }
        return result
    }

    /// 한자 문자열의 독음을 한 글자씩 찾아 연결하여 반환 (캐시 사용)
    private func getReadingForHanja(_ hanja: String) -> String {
        var result = ""
        for char in hanja {
            let charStr = String(char)
            if let cached = readingCache[charStr] {
                result += cached
                continue
            }
            let sql = "SELECT hangul_reading, korean_reading FROM hanja WHERE character = ?"
            var stmt: OpaquePointer?
            if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (charStr as NSString).utf8String, -1, nil)
                if sqlite3_step(stmt) == SQLITE_ROW {
                    let hangul = sqlite3_column_text(stmt, 0).map { String(cString: $0) } ?? ""
                    if !hangul.isEmpty {
                        readingCache[charStr] = hangul
                        result += hangul
                    } else if let raw = sqlite3_column_text(stmt, 1) {
                        let roman = String(cString: raw).lowercased().split(separator: " ").first.map(String.init) ?? ""
                        let converted = Self.romanMap[roman] ?? roman
                        readingCache[charStr] = converted
                        result += converted
                    }
                } else {
                    readingCache[charStr] = charStr
                    result += charStr
                }
            }
            sqlite3_finalize(stmt)
        }
        return result
    }

    func clauseReadingPublic(_ clause: String) -> String {
        return clauseReading(clause)
    }

    /// 단일 한자의 독음 반환
    func readingForChar(_ charStr: String) -> String? {
        let sql = "SELECT hangul_reading, korean_reading FROM hanja WHERE character = ?"
        var stmt: OpaquePointer?
        defer { sqlite3_finalize(stmt) }
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else { return nil }
        sqlite3_bind_text(stmt, 1, (charStr as NSString).utf8String, -1, nil)
        guard sqlite3_step(stmt) == SQLITE_ROW else { return nil }
        let hangul = sqlite3_column_text(stmt, 0).map { String(cString: $0) } ?? ""
        if !hangul.isEmpty { return hangul }
        if let raw = sqlite3_column_text(stmt, 1) {
            let roman = String(cString: raw).lowercased().split(separator: " ").first.map(String.init) ?? ""
            return Self.romanMap[roman] ?? roman
        }
        return nil
    }

    /// 단일 한자의 뜻 반환
    func definitionForChar(_ charStr: String) -> String? {
        let sql = "SELECT definition_ko, definition FROM hanja WHERE character = ?"
        var stmt: OpaquePointer?
        defer { sqlite3_finalize(stmt) }
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else { return nil }
        sqlite3_bind_text(stmt, 1, (charStr as NSString).utf8String, -1, nil)
        guard sqlite3_step(stmt) == SQLITE_ROW else { return nil }
        let defKo = sqlite3_column_text(stmt, 0).map { String(cString: $0) } ?? ""
        if !defKo.isEmpty { return defKo }
        let defEn = sqlite3_column_text(stmt, 1).map { String(cString: $0) } ?? ""
        return defEn.isEmpty ? nil : defEn
    }

    private func clauseReading(_ clause: String) -> String {
        var result = ""
        for char in clause {
            let scalar = char.unicodeScalars.first?.value ?? 0
            let isHanja = (scalar >= 0x4E00 && scalar <= 0x9FFF) || (scalar >= 0x3400 && scalar <= 0x4DBF)
            guard isHanja else {
                result += String(char)
                continue
            }

            let charStr = String(char)
            let sql = "SELECT hangul_reading, korean_reading FROM hanja WHERE character = ?"
            var stmt: OpaquePointer?
            if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (charStr as NSString).utf8String, -1, nil)
                if sqlite3_step(stmt) == SQLITE_ROW {
                    let hangul = sqlite3_column_text(stmt, 0).map { String(cString: $0) } ?? ""
                    if !hangul.isEmpty {
                        result += hangul
                    } else if let raw = sqlite3_column_text(stmt, 1) {
                        let roman = String(cString: raw).lowercased().split(separator: " ").first.map(String.init) ?? ""
                        result += Self.romanMap[roman] ?? roman
                    }
                } else {
                    result += charStr
                }
            }
            sqlite3_finalize(stmt)
        }
        return result
    }

    deinit {
        sqlite3_close(db)
    }

    // MARK: - 로마자 독음 → 한글 변환
    private static let romanMap: [String: String] = [
        "ka": "가", "kak": "각", "kan": "간", "kal": "갈", "kam": "감", "kap": "갑", "kang": "강",
        "kay": "개", "kayk": "객",
        "ke": "거", "ken": "건", "kel": "걸", "kem": "검", "kep": "겁",
        "kyek": "격", "kyen": "견", "kyel": "결", "kyem": "겸", "kyeng": "경",
        "ko": "고", "kok": "곡", "kon": "곴", "kol": "골", "kong": "공", "kwa": "과", "kwan": "관", "kwang": "광",
        "koy": "괴", "kwu": "구", "kwuk": "국", "kwun": "군", "kwul": "굴", "kwung": "궁",
        "kwey": "귀", "kyu": "규", "kyun": "균", "kuk": "극", "kun": "그", "kum": "금", "kup": "급",
        "ki": "기", "kil": "길",
        "na": "나", "nak": "낙", "nan": "난", "nam": "남", "nap": "납",
        "nay": "내", "nyek": "녀",
        "no": "노", "nok": "녹", "nong": "농", "noy": "뇌",
        "nwu": "누", "nung": "능", "ni": "니",
        "ta": "다", "tak": "닥", "tan": "단", "tal": "달", "tam": "담", "tap": "답", "tang": "당",
        "tay": "대", "tek": "덕",
        "to": "도", "tok": "독", "ton": "돈", "tol": "돌", "tong": "동", "twu": "두", "twung": "둥",
        "tuk": "득",
        "tung": "등",
        "la": "라", "lak": "락", "lan": "란", "lam": "람", "lang": "랑",
        "lay": "래", "lyang": "량", "lyek": "력", "lyen": "련", "lyel": "렬", "lyem": "렴", "lyeng": "령",
        "lo": "로", "lok": "록", "lon": "론", "long": "롱",
        "lwu": "루", "lyu": "류", "lyuk": "륙", "lyun": "률", "lyul": "르",
        "lung": "릅", "li": "리", "lim": "림", "lip": "립",
        "ma": "마", "mak": "막", "man": "만", "mal": "말", "mang": "망",
        "may": "매", "mayk": "맥",
        "mek": "멍", "men": "면", "myel": "멸", "myeng": "명",
        "mo": "모", "mok": "목", "mol": "몫", "mong": "몽", "mwu": "무", "mwun": "문", "mwul": "물",
        "mi": "미", "min": "민", "mil": "밀",
        "pa": "바", "pak": "박", "pan": "반", "pal": "발", "pang": "방",
        "pay": "배", "payk": "백", "pen": "번", "pel": "벌", "pep": "법",
        "pyel": "별", "pyeng": "병",
        "po": "보", "pok": "복", "pon": "본", "pong": "보",
        "pwu": "부", "pwuk": "북", "pwun": "분", "pwul": "불",
        "pi": "비", "pin": "빈", "ping": "빙",
        "sa": "사", "sak": "삭", "san": "산", "sal": "살", "sam": "삼", "sang": "상",
        "say": "새", "sayk": "색",
        "se": "세", "sek": "석", "sen": "선", "sel": "설", "sem": "섬", "sep": "섭", "seng": "성",
        "so": "소", "sok": "속", "son": "손", "song": "송",
        "swu": "수", "swuk": "숙", "swun": "순", "swul": "술", "sung": "승",
        "si": "시", "sik": "식", "sin": "신", "sil": "실", "sim": "심", "sip": "십",
        "a": "아", "ak": "악", "an": "안", "al": "알", "am": "암", "ap": "압", "ang": "앙",
        "ay": "애", "ayk": "액",
        "ya": "야", "yak": "약", "yang": "양",
        "e": "어", "en": "언", "el": "얼", "em": "엄", "ep": "업",
        "ye": "예",
        "o": "오", "ok": "옥", "on": "온", "ol": "올", "ong": "옹", "wa": "와", "wan": "완", "wang": "왕",
        "oy": "외", "yo": "요", "yok": "욕", "yong": "용",
        "wu": "우", "wun": "운", "wul": "울", "wung": "웅", "wen": "원", "wel": "월", "wi": "위",
        "yu": "유", "yuk": "육", "yun": "윤", "yul": "율", "yung": "융",
        "un": "은", "ul": "을", "um": "음", "up": "읍", "ung": "응",
        "uy": "의", "i": "이", "ik": "익", "in": "인", "il": "일", "im": "임", "ip": "입",
        "ca": "자", "cak": "작", "can": "잔", "cam": "잠", "cap": "잡", "cang": "장",
        "cay": "재",
        "ce": "저", "cek": "적", "cen": "전", "cel": "절", "cem": "점", "cep": "접", "ceng": "정",
        "co": "조", "cok": "족", "con": "존", "cong": "종",
        "cwu": "주", "cwuk": "죽", "cwun": "준", "cwung": "중",
        "cung": "증", "ci": "지", "cik": "직", "cin": "진", "cil": "질", "cim": "짐", "cip": "집",
        "cha": "차", "chak": "착", "chan": "찬", "chal": "찰", "cham": "참", "chang": "창",
        "chay": "채", "chayk": "책",
        "che": "처", "chek": "척", "chen": "천", "chel": "철", "chem": "첨", "chep": "첩", "cheng": "청",
        "cho": "초", "chok": "촉", "chon": "촌", "chong": "총",
        "chwu": "추", "chwuk": "축", "chwun": "춘", "chwung": "충",
        "chi": "치", "chik": "칙", "chin": "친", "chil": "칠", "chim": "침", "chip": "칩",
        "tha": "타", "thak": "탁", "than": "탄", "thal": "탈", "thang": "탕",
        "thay": "태",
        "the": "터",
        "tho": "토", "thong": "통",
        "thwu": "투", "thuk": "특",
        "pha": "파", "phan": "판", "phal": "팔", "phang": "팡",
        "phay": "패", "phyen": "편", "phyeng": "평",
        "pho": "포",
        "phwu": "푸", "phwung": "풍",
        "phi": "피", "phik": "필", "phil": "필",
        "ha": "하", "hak": "학", "han": "한", "hal": "할", "ham": "함", "hap": "합", "hang": "항",
        "hay": "해", "hayk": "핵",
        "he": "허", "hen": "헌", "hel": "헐", "hem": "험", "hyel": "혈", "hyen": "현", "hyeng": "형",
        "ho": "호", "hok": "혹", "hon": "혼", "hong": "홍", "hwa": "화", "hwan": "환", "hwang": "황",
        "hoy": "회", "hoyk": "획", "hwu": "후", "hwun": "훈",
        "hyu": "휴", "hyung": "흥",
        "hung": "흥", "hi": "희",
    ]

    static func romanToHangul(_ roman: String) -> String {
        // 공백으로 구분된 복수 독음 처리
        let parts = roman.split(separator: " ").map(String.init)
        let converted = parts.map { romanMap[$0] ?? $0 }
        return converted.joined(separator: " ")
    }
}
