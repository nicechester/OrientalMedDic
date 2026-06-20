import SwiftUI
import Combine

@MainActor
class ResultViewModel: ObservableObject {
    @Published var dbResults: [DBResult] = []

    private let db = DictionaryDB.shared

    func lookupDB(text: String) {
        // Check if input contains Hangul
        let containsHangul = text.rangeOfCharacter(from: .koreanLetters) != nil
        
        if containsHangul {
            dbResults = db.lookupByReading(text: text)
        } else {
            dbResults = db.lookupAllSubstrings(text: text)
        }
    }
}
