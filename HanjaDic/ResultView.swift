import SwiftUI
import Combine

struct DBResult: Identifiable {
    let id = UUID()
    let term: String
    let reading: String
    let category: String?
    let description: String
}

@MainActor
class ResultViewModel: ObservableObject {
    @Published var dbResults: [DBResult] = []

    private let db = DictionaryDB.shared

    func lookupDB(text: String) {
        dbResults = db.lookupAllSubstrings(text: text)
    }
}

struct ResultDetailSheet: View {
    let result: DBResult
    @StateObject private var viewModel = ResultDetailViewModel(term: "")

    init(result: DBResult) {
        self.result = result
        _viewModel = StateObject(wrappedValue: ResultDetailViewModel(term: result.term))
    }

    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 16) {
                Text(result.term)
                    .font(.system(size: 36))
                Text(result.reading)
                    .font(.title2)
                    .foregroundStyle(.red)
            }

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    let wordResults = viewModel.results.filter { $0.category == "한자어" }
                    if !wordResults.isEmpty {
                        Section {
                            ForEach(wordResults, id: \.term) { res in
                                resultRow(res)
                            }
                        } header: {
                            Text("한자어")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.indigo)
                        }
                    }

                    let herbalResults = viewModel.results.filter { $0.category == "본초" }
                    if !herbalResults.isEmpty {
                        Section {
                            ForEach(herbalResults, id: \.term) { res in
                                resultRow(res)
                            }
                        } header: {
                            Text("본초 (약재)")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.blue)
                        }
                    }

                    let formulaResults = viewModel.results.filter { $0.category == "방제" }
                    if !formulaResults.isEmpty {
                        Section {
                            ForEach(formulaResults, id: \.term) { res in
                                resultRow(res)
                            }
                        } header: {
                            Text("방제 (처방)")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.purple)
                        }
                    }

                    let acupointResults = viewModel.results.filter { $0.category == "경혈" }
                    if !acupointResults.isEmpty {
                        Section {
                            ForEach(acupointResults, id: \.term) { res in
                                resultRow(res)
                            }
                        } header: {
                            Text("경혈 (침구)")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.teal)
                        }
                    }

                    let diseaseResults = viewModel.results.filter { $0.category == "병명" }
                    if !diseaseResults.isEmpty {
                        Section {
                            ForEach(diseaseResults, id: \.term) { res in
                                resultRow(res)
                            }
                        } header: {
                            Text("병명 (질병)")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.orange)
                        }
                    }

                    if !result.description.isEmpty {
                        Section {
                            Text(result.description)
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        } header: {
                            Text("설명")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.gray)
                        }
                    }

                    let charResults = viewModel.results.filter { $0.category == nil }
                    if !charResults.isEmpty {
                        Section {
                            ForEach(charResults, id: \.term) { res in
                                resultRow(res)
                            }
                        } header: {
                            Text("글자 정보")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.gray)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding()
    }

    private func resultRow(_ res: DBResult) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text(res.term)
                    .font(.headline)
                    .foregroundStyle(.black)
                Text(res.reading)
                    .font(.subheadline)
                    .foregroundStyle(.red)
            }
            Text(res.description)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(3)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

@MainActor
class ResultDetailViewModel: ObservableObject {
    @Published var results: [DBResult] = []

    init(term: String) {
        self.results = DictionaryDB.shared.lookupAllSubstrings(text: term)
    }
}
