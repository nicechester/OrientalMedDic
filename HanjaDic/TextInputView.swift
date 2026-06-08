import SwiftUI

struct TextInputView: View {
    @State private var inputText = ""
    @State private var showResult = false
    @Binding var searchQuery: String

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                TextEditor(text: $inputText)
                    .font(.title2)
                    .frame(height: 150)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(.secondary.opacity(0.3)))
                    .padding(.horizontal)

                if inputText.isEmpty {
                    Text("한자 또는 의서 문장을 입력하세요")
                        .foregroundStyle(.secondary)
                }

                Button(action: { showResult = true }) {
                    Label("해석하기", systemImage: "text.magnifyingglass")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(.blue)
                        .foregroundStyle(.white)
                        .cornerRadius(12)
                }
                .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty)
                .padding(.horizontal)

                Spacer()
            }
            .padding(.top)
            .navigationTitle("한자 입력")
            .sheet(isPresented: $showResult) {
                TextInputResultView(inputText: inputText)
            }
            .task(id: searchQuery) {
                if !searchQuery.isEmpty {
                    inputText = searchQuery
                    try? await Task.sleep(for: .milliseconds(100))
                    showResult = true
                    searchQuery = ""
                }
            }
        }
    }
}
