import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var searchQuery = ""
    @StateObject private var cameraViewModel = CameraViewModel()

    var body: some View {
        TabView(selection: $selectedTab) {
            CameraView(viewModel: cameraViewModel)
                .tabItem {
                    Image(systemName: "camera.fill")
                    Text("스캔")
                }
                .tag(0)

            OverlayReadingView()
                .tabItem {
                    Image(systemName: "character.magnify")
                    Text("독음")
                }
                .tag(1)

            TextInputView(searchQuery: $searchQuery)
                .tabItem {
                    Image(systemName: "character.textbox")
                    Text("입력")
                }
                .tag(2)

            SettingsView()
                .tabItem {
                    Image(systemName: "gearshape")
                    Text("설정")
                }
                .tag(3)
        }
        .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("SearchWord"))) { notification in
            if let word = notification.userInfo?["word"] as? String {
                searchQuery = word
                selectedTab = 2
            }
        }
        .onAppear {
            let appearance = UITabBarAppearance()
            appearance.configureWithDefaultBackground()
            UITabBar.appearance().scrollEdgeAppearance = appearance
            UITabBar.appearance().standardAppearance = appearance
        }
    }
}
