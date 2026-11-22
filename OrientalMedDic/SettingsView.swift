import SwiftUI

struct SettingsView: View {
    @ObservedObject private var settings = AppSettings.shared

    var body: some View {
        NavigationView {
            Form {
                Section(
                    header: Text("자동 독음"),
                    footer: Text("화면을 다시 스캔하는 간격입니다. 탭 모드와 자동 모드에 모두 적용됩니다.")
                ) {
                    Stepper(
                        value: $settings.autoScanInterval,
                        in: AppSettings.autoScanIntervalRange,
                        step: 1
                    ) {
                        HStack {
                            Text("스캔 간격")
                            Spacer()
                            Text("\(Int(settings.autoScanInterval))초")
                                .foregroundColor(.secondary)
                        }
                    }
                }

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
