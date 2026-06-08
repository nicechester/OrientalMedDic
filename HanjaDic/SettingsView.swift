import SwiftUI

struct SettingsView: View {
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("정보")) {
                    HStack {
                        Text("버전")
                        Spacer()
                        Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("설정")
        }
    }
}
