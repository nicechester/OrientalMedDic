import SwiftUI
import Combine

enum ReadingMode: String {
    /// Tap a box to reveal its reading (auto-hides after 20s).
    case tap
    /// Every detected word shows its reading as an overlay.
    case auto
}

class AppSettings: ObservableObject {
    static let shared = AppSettings()

    private static let readingModeKey = "readingMode"
    private static let autoScanIntervalKey = "autoScanInterval"

    /// Allowed range for the auto-mode scan interval, in seconds.
    static let autoScanIntervalRange: ClosedRange<Double> = 1...10
    static let defaultAutoScanInterval: Double = 5

    @Published var readingMode: ReadingMode {
        didSet { UserDefaults.standard.set(readingMode.rawValue, forKey: Self.readingModeKey) }
    }

    /// Minimum time between OCR scans in auto mode, in seconds.
    @Published var autoScanInterval: Double {
        didSet { UserDefaults.standard.set(autoScanInterval, forKey: Self.autoScanIntervalKey) }
    }

    private init() {
        let raw = UserDefaults.standard.string(forKey: Self.readingModeKey) ?? ""
        readingMode = ReadingMode(rawValue: raw) ?? .tap

        let storedInterval = UserDefaults.standard.object(forKey: Self.autoScanIntervalKey) as? Double
        autoScanInterval = storedInterval ?? Self.defaultAutoScanInterval
    }
}
