import SwiftUI

struct TextInputResultView: View {
    let inputText: String
    @StateObject private var viewModel = ResultViewModel()
    @Environment(\.dismiss) private var dismiss
    @State private var selectedResult: DBResult?

    var body: some View {
        ZStack {
            VStack(spacing: 0) {
                HStack {
                    Text("검색 결과")
                        .font(.headline)
                    Spacer()
                }
                .padding()

                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        if !viewModel.dbResults.isEmpty {
                            ForEach(viewModel.dbResults, id: \.id) { result in
                                Button(action: { selectedResult = result }) {
                                    HStack(alignment: .top, spacing: 8) {
                                        Text(result.term)
                                            .font(.headline)
                                            .foregroundStyle(.black)
                                        Text(result.reading)
                                            .font(.subheadline)
                                            .foregroundStyle(.red)
                                        if let category = result.category {
                                            Text(category)
                                                .font(.caption)
                                                .padding(.horizontal, 6)
                                                .padding(.vertical, 2)
                                                .background(.orange.opacity(0.2))
                                                .cornerRadius(4)
                                        }
                                        Spacer()
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                }
                                .padding(.vertical, 4)

                                Text(result.description)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(3)
                            }
                        } else {
                            Text("검색 결과가 없습니다")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                                .frame(maxWidth: .infinity, alignment: .center)
                                .padding()
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
                            Text("닫기")
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
        .sheet(item: $selectedResult) { result in
            ResultDetailSheet(result: result)
                .presentationDetents([.medium])
        }
        .onAppear {
            viewModel.lookupDB(text: inputText)
        }
    }
}
