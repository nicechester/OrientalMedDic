import SwiftUI
import Vision
import PhotosUI
import Combine
import AVFoundation

struct OverlayReadingView: View {
    @StateObject private var viewModel = OverlayViewModel()
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedItem: OverlayItem?

    var body: some View {
        NavigationStack {
            ZStack {
                if let capturedImage = viewModel.capturedImage {
                    staticOverlayView(image: capturedImage)
                } else {
                    liveCameraView
                }
            }
            .navigationTitle("독음 오버레이")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $selectedItem) { item in
                CharDetailSheet(item: item)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
            .onChange(of: selectedPhoto) { _, item in
                guard let item else { return }
                Task {
                    if let data = try? await item.loadTransferable(type: Data.self),
                       let uiImage = UIImage(data: data) {
                        viewModel.processImage(uiImage)
                    }
                    selectedPhoto = nil
                }
            }
        }
    }

    // MARK: - 실시간 카메라 뷰

    @State private var cameraZoom: CGFloat = 1.0
    @State private var lastCameraZoom: CGFloat = 1.0

    private var liveCameraView: some View {
        GeometryReader { geo in
            ZStack {
                LiveCameraPreview(session: viewModel.session)
                    .onTapGesture {
                        viewModel.dismissReading()
                    }

                // 실시간 오버레이 — 바운딩 박스 + 탭 토글 독음 + 사전 아이콘
                ForEach(viewModel.overlayItems) { item in
                    let rect = convertVisionToScreen(normalizedBox: item.box, geoSize: geo.size)
                    wordBox(item: item, rect: rect)
                }

                // 하단 버튼
                VStack {
                    Spacer()
                    HStack(spacing: 16) {
                        PhotosPicker(selection: $selectedPhoto, matching: .images) {
                            Image(systemName: "photo.on.rectangle")
                                .font(.system(size: 28))
                                .foregroundStyle(.white)
                                .frame(width: 50, height: 50)
                                .background(.ultraThinMaterial)
                                .clipShape(Circle())
                        }

                        Text(String(format: "%.1f×", cameraZoom))
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(.white)
                            .frame(minWidth: 45).frame(height: 32)
                            .background(Color.black.opacity(0.5))
                            .cornerRadius(8)

                        Button(action: {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                cameraZoom = 1.0; lastCameraZoom = 1.0
                                viewModel.setZoom(1.0)
                            }
                        }) {
                            Image(systemName: "arrow.down.left.and.arrow.up.right")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundStyle(.white)
                                .frame(width: 32, height: 32)
                                .background(Color.blue.opacity(0.6))
                                .cornerRadius(6)
                        }
                    }
                    .padding(.bottom, 120)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
            }
            .gesture(
                MagnifyGesture()
                    .onChanged { value in
                        let newZoom = lastCameraZoom * value.magnification
                        cameraZoom = newZoom
                        viewModel.setZoom(newZoom)
                    }
                    .onEnded { _ in lastCameraZoom = cameraZoom }
            )
        }
        .ignoresSafeArea()
        .onAppear { viewModel.startLiveOCR() }
        .onDisappear { viewModel.stopLiveOCR() }
        .onReceive(NotificationCenter.default.publisher(for: UIDevice.orientationDidChangeNotification)) { _ in
            viewModel.updateVideoOutputRotation()
            viewModel.overlayItems = []
        }
    }

    // MARK: - 정적 이미지 오버레이 뷰

    @State private var zoomScale: CGFloat = 1.0
    @State private var lastZoomScale: CGFloat = 1.0
    @State private var offset: CGSize = .zero
    @State private var lastOffset: CGSize = .zero

    private func staticOverlayView(image: UIImage) -> some View {
        GeometryReader { geo in
            let displayRect = calculateDisplayRect(imageSize: image.size, geoSize: geo.size)

            ZStack {
                ZStack {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)

                    ForEach(viewModel.overlayItems) { item in
                        let rect = convertToScreen(normalizedBox: item.box, displayRect: displayRect)
                        wordBox(item: item, rect: rect)
                    }
                }
                .scaleEffect(zoomScale)
                .offset(offset)
                .gesture(
                    MagnifyGesture()
                        .onChanged { value in zoomScale = lastZoomScale * value.magnification }
                        .onEnded { _ in
                            lastZoomScale = max(zoomScale, 1.0)
                            zoomScale = lastZoomScale
                        }
                )
                .simultaneousGesture(
                    DragGesture()
                        .onChanged { value in
                            offset = CGSize(
                                width: lastOffset.width + value.translation.width,
                                height: lastOffset.height + value.translation.height
                            )
                        }
                        .onEnded { _ in lastOffset = offset }
                )
                .onTapGesture(count: 2) {
                    withAnimation {
                        zoomScale = 1.0; lastZoomScale = 1.0
                        offset = .zero; lastOffset = .zero
                    }
                }

                VStack {
                    Spacer()
                    HStack(spacing: 12) {
                        Button(action: {
                            viewModel.capturedImage = nil
                            viewModel.overlayItems = []
                            viewModel.startLiveOCR()
                        }) {
                            Image(systemName: "xmark")
                                .font(.system(size: 18, weight: .semibold))
                                .foregroundStyle(.white)
                                .frame(width: 44, height: 44)
                                .background(Color.gray.opacity(0.6))
                                .cornerRadius(22)
                        }

                        Text(String(format: "%.1f×", zoomScale))
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundStyle(.white)
                            .frame(minWidth: 45).frame(height: 32)
                            .background(Color.black.opacity(0.5))
                            .cornerRadius(8)

                        Button(action: {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                zoomScale = 1.0; lastZoomScale = 1.0
                                offset = .zero; lastOffset = .zero
                            }
                        }) {
                            Image(systemName: "arrow.down.left.and.arrow.up.right")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundStyle(.white)
                                .frame(width: 32, height: 32)
                                .background(Color.blue.opacity(0.6))
                                .cornerRadius(6)
                        }

                        Spacer()
                    }
                    .padding(.bottom, 120)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .ignoresSafeArea()
    }

    // MARK: - 단어 박스 (공통)

    @ViewBuilder
    private func wordBox(item: OverlayItem, rect: CGRect) -> some View {
        let isVisible = viewModel.visibleReading == item.id
        let fontSize: CGFloat = 24

        // 바운딩 박스
        RoundedRectangle(cornerRadius: 3)
            .stroke(Color.yellow.opacity(0.8), lineWidth: 1.5)
            .frame(width: rect.width, height: rect.height)
            .contentShape(Rectangle().size(CGSize(width: rect.width + 20, height: rect.height + 20)))
            .position(x: rect.midX, y: rect.midY)
            .onTapGesture { viewModel.toggleReading(for: item.id) }

        // 독음 박스 (바운딩박스 위에 독립적으로 표시)
        if isVisible {
            HStack(spacing: 4) {
                Text(item.reading)
                    .font(.system(size: fontSize))
                    .foregroundStyle(.black)
                    .fixedSize()

                Image(systemName: "book.closed.fill")
                    .font(.system(size: fontSize * 0.7))
                    .foregroundStyle(.white)
                    .padding(2)
                    .background(Color.blue.opacity(0.75))
                    .clipShape(RoundedRectangle(cornerRadius: 3))
                    .onTapGesture { selectedItem = item }
            }
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            .background(Color.white.opacity(0.95))
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .shadow(radius: 2)
            .position(x: rect.midX, y: rect.minY - fontSize)
        }
    }

    // MARK: - 좌표 변환

    private func convertVisionToScreen(normalizedBox: CGRect, geoSize: CGSize) -> CGRect {
        let frameAspect = viewModel.cameraFrameAspect
        let screenAspect = geoSize.width / geoSize.height

        let scaleX: CGFloat
        let scaleY: CGFloat
        let offsetX: CGFloat
        let offsetY: CGFloat

        if frameAspect > screenAspect {
            scaleY = geoSize.height
            scaleX = geoSize.height * frameAspect
            offsetX = (scaleX - geoSize.width) / 2
            offsetY = 0
        } else {
            scaleX = geoSize.width
            scaleY = geoSize.width / frameAspect
            offsetX = 0
            offsetY = (scaleY - geoSize.height) / 2
        }

        let x = normalizedBox.origin.x * scaleX - offsetX
        let y = (1 - normalizedBox.origin.y - normalizedBox.height) * scaleY - offsetY
        let w = normalizedBox.width * scaleX
        let h = normalizedBox.height * scaleY
        return CGRect(x: x, y: y, width: w, height: h)
    }

    private func calculateDisplayRect(imageSize: CGSize, geoSize: CGSize) -> CGRect {
        let imageAspect = imageSize.width / imageSize.height
        let screenAspect = geoSize.width / geoSize.height
        if imageAspect > screenAspect {
            let displayW = geoSize.width
            let displayH = displayW / imageAspect
            return CGRect(x: 0, y: (geoSize.height - displayH) / 2, width: displayW, height: displayH)
        } else {
            let displayH = geoSize.height
            let displayW = displayH * imageAspect
            return CGRect(x: (geoSize.width - displayW) / 2, y: 0, width: displayW, height: displayH)
        }
    }

    private func convertToScreen(normalizedBox: CGRect, displayRect: CGRect) -> CGRect {
        let x = displayRect.origin.x + normalizedBox.origin.x * displayRect.width
        let y = displayRect.origin.y + (1 - normalizedBox.origin.y - normalizedBox.height) * displayRect.height
        let w = normalizedBox.width * displayRect.width
        let h = normalizedBox.height * displayRect.height
        return CGRect(x: x, y: y, width: w, height: h)
    }
}

// MARK: - 글자 상세 팝업

struct CharDetailSheet: View {
    let item: OverlayItem
    @StateObject private var viewModel: CharDetailViewModel

    init(item: OverlayItem) {
        self.item = item
        _viewModel = StateObject(wrappedValue: CharDetailViewModel(character: item.character))
    }

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                HStack(spacing: 16) {
                    Text(item.character)
                        .font(.system(size: 36))
                    Text(item.reading)
                        .font(.title2)
                        .foregroundStyle(.red)
                }
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title2)
                        .foregroundStyle(.gray)
                }
            }

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    let wordResults = viewModel.results.filter { $0.category == "한자어" }
                    if !wordResults.isEmpty {
                        Section {
                            ForEach(wordResults, id: \.term) { result in resultRow(result) }
                        } header: {
                            Text("한자어").font(.caption).fontWeight(.semibold).foregroundStyle(.indigo)
                        }
                    }

                    let herbalResults = viewModel.results.filter { $0.category == "본초" }
                    if !herbalResults.isEmpty {
                        Section {
                            ForEach(herbalResults, id: \.term) { result in resultRow(result) }
                        } header: {
                            Text("본초 (약재)").font(.caption).fontWeight(.semibold).foregroundStyle(.blue)
                        }
                    }

                    let formulaResults = viewModel.results.filter { $0.category == "방제" }
                    if !formulaResults.isEmpty {
                        Section {
                            ForEach(formulaResults, id: \.term) { result in resultRow(result) }
                        } header: {
                            Text("방제 (처방)").font(.caption).fontWeight(.semibold).foregroundStyle(.purple)
                        }
                    }

                    let acupointResults = viewModel.results.filter { $0.category == "경혈" }
                    if !acupointResults.isEmpty {
                        Section {
                            ForEach(acupointResults, id: \.term) { result in resultRow(result) }
                        } header: {
                            Text("경혈 (침구)").font(.caption).fontWeight(.semibold).foregroundStyle(.teal)
                        }
                    }

                    let diseaseResults = viewModel.results.filter { $0.category == "병명" }
                    if !diseaseResults.isEmpty {
                        Section {
                            ForEach(diseaseResults, id: \.term) { result in resultRow(result) }
                        } header: {
                            Text("병명 (질병)").font(.caption).fontWeight(.semibold).foregroundStyle(.orange)
                        }
                    }

                    if !item.definition.isEmpty {
                        Section {
                            Text(item.definition).font(.callout).foregroundStyle(.secondary)
                        } header: {
                            Text("글자 정보").font(.caption).fontWeight(.semibold).foregroundStyle(.gray)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding()
    }

    private func resultRow(_ result: DBResult) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text(result.term).font(.headline).foregroundStyle(.black)
                Text(result.reading).font(.subheadline).foregroundStyle(.red)
            }
            Text(result.description).font(.caption).foregroundStyle(.secondary).lineLimit(3)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

@MainActor
class CharDetailViewModel: ObservableObject {
    @Published var results: [DBResult] = []

    init(character: String) {
        self.results = DictionaryDB.shared.lookupAllSubstrings(text: character)
    }
}


// MARK: - Live Camera Preview

struct LiveCameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> UIView {
        let view = LivePreviewUIView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }
    func updateUIView(_ uiView: UIView, context: Context) {}

    class LivePreviewUIView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
        override func layoutSubviews() {
            super.layoutSubviews()
            previewLayer.frame = bounds
            guard let connection = previewLayer.connection else { return }
            let orientation = window?.windowScene?.interfaceOrientation ?? .portrait
            let angle: CGFloat = switch orientation {
            case .landscapeRight: 0
            case .landscapeLeft: 180
            case .portraitUpsideDown: 270
            default: 90
            }
            if connection.isVideoRotationAngleSupported(angle) {
                connection.videoRotationAngle = angle
            }
        }
    }
}

// MARK: - 오버레이 아이템

struct OverlayItem: Identifiable {
    let id = UUID()
    let character: String
    let reading: String
    let definition: String
    let box: CGRect
}

// MARK: - ViewModel

@MainActor
class OverlayViewModel: NSObject, ObservableObject {
    @Published var overlayItems: [OverlayItem] = []
    @Published var visibleReading: UUID? = nil
    @Published var capturedImage: UIImage?
    @Published var isProcessing = false
    @Published var cameraFrameAspect: CGFloat = 3.0 / 4.0

    let session = AVCaptureSession()
    private var device: AVCaptureDevice?
    private let db = DictionaryDB.shared

    private let videoOutput = AVCaptureVideoDataOutput()
    private let processingQueue = DispatchQueue(label: "ocr.processing")
    private var liveOCRActive = false
    private var isOCRProcessing = false
    private var frameSize: CGSize = CGSize(width: 1080, height: 1920)
    private var lastFrameImage: UIImage?
    private var readingTimer: Task<Void, Never>? = nil

    func dismissReading() {
        visibleReading = nil
        readingTimer?.cancel()
        readingTimer = nil
    }

    func toggleReading(for id: UUID) {
        if visibleReading == id {
            // 수동 off: 즉시 숨김 + 타이머 취소
            visibleReading = nil
            readingTimer?.cancel()
            readingTimer = nil
        } else {
            // on: 이전 타이머 취소 후 새 단어 표시 + 20초 타이머
            readingTimer?.cancel()
            visibleReading = id
            readingTimer = Task { @MainActor [weak self] in
                try? await Task.sleep(for: .seconds(20))
                guard !Task.isCancelled else { return }
                self?.visibleReading = nil
                self?.readingTimer = nil
            }
        }
    }

    func startLiveOCR() {
        liveOCRActive = true
        capturedImage = nil
        visibleReading = nil
        readingTimer?.cancel()
        readingTimer = nil

        if session.inputs.isEmpty {
            guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
                  let input = try? AVCaptureDeviceInput(device: device) else { return }
            self.device = device

            session.beginConfiguration()
            if session.canAddInput(input) { session.addInput(input) }
            videoOutput.setSampleBufferDelegate(self, queue: processingQueue)
            videoOutput.alwaysDiscardsLateVideoFrames = true
            if session.canAddOutput(videoOutput) { session.addOutput(videoOutput) }
            session.commitConfiguration()
        } else {
            videoOutput.setSampleBufferDelegate(self, queue: processingQueue)
        }

        updateVideoOutputRotation()
        DispatchQueue.global(qos: .userInitiated).async { self.session.startRunning() }
    }

    func stopLiveOCR() {
        liveOCRActive = false
        isOCRProcessing = true
        DispatchQueue.global(qos: .userInitiated).async { self.session.stopRunning() }
    }

    func updateVideoOutputRotation() {
        guard let connection = videoOutput.connection(with: .video) else { return }
        let orientation = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }.first?.interfaceOrientation ?? .portrait
        let angle: CGFloat = switch orientation {
        case .landscapeRight: 180.0
        case .landscapeLeft: 0.0
        case .portraitUpsideDown: 270.0
        default: 90.0
        }
        if connection.isVideoRotationAngleSupported(angle) {
            connection.videoRotationAngle = angle
        }
    }

    func setZoom(_ factor: CGFloat) {
        guard let device else { return }
        let zoom = max(1.0, min(factor, device.activeFormat.videoMaxZoomFactor, 10.0))
        do {
            try device.lockForConfiguration()
            device.videoZoomFactor = zoom
            device.unlockForConfiguration()
        } catch {}
    }

    // MARK: - 정적 이미지 처리 (갤러리)

    func processImage(_ image: UIImage) {
        stopLiveOCR()
        isProcessing = true
        visibleReading = nil
        readingTimer?.cancel()
        readingTimer = nil
        let normalized = normalizeOrientation(image)
        guard let cgImage = normalized.cgImage else {
            isProcessing = false
            return
        }
        performOCR(on: cgImage, usePreprocessing: true) { [weak self] items in
            Task { @MainActor in
                self?.overlayItems = items
                self?.capturedImage = normalized
                self?.isProcessing = false
            }
        }
    }

    private func normalizeOrientation(_ image: UIImage) -> UIImage {
        guard image.imageOrientation != .up else { return image }

        let contextSize: CGSize
        let drawRect: CGRect

        switch image.imageOrientation {
        case .right, .left:
            contextSize = CGSize(width: image.size.height, height: image.size.width)
            drawRect = CGRect(x: 0, y: 0, width: image.size.height, height: image.size.width)
        default:
            contextSize = image.size
            drawRect = CGRect(origin: .zero, size: image.size)
        }

        UIGraphicsBeginImageContextWithOptions(contextSize, false, image.scale)
        image.draw(in: drawRect)
        let normalized = UIGraphicsGetImageFromCurrentImageContext() ?? image
        UIGraphicsEndImageContext()
        return normalized
    }

    // MARK: - OCR

    private func performOCR(on cgImage: CGImage, usePreprocessing: Bool = false, completion: @escaping ([OverlayItem]) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { completion([]); return }

            let processedImage = usePreprocessing
                ? ImagePreprocessor.preprocess(cgImage) ?? cgImage
                : cgImage

            let request = VNRecognizeTextRequest()
            request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
            request.recognitionLevel = .accurate
            request.minimumTextHeight = 0.0

            let handler = VNImageRequestHandler(cgImage: processedImage, options: [:])
            try? handler.perform([request])

            guard let observations = request.results else { completion([]); return }
            let items = self.buildOverlayItemsFromObservations(observations)
            completion(items)
        }
    }

    nonisolated private func buildOverlayItemsFromObservations(_ observations: [VNRecognizedTextObservation]) -> [OverlayItem] {
        var items: [OverlayItem] = []
        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let str = candidate.string
            let indices = Array(str.indices)

            var i = 0
            while i < indices.count {
                let char = str[indices[i]]
                let scalar = char.unicodeScalars.first?.value ?? 0
                let isHanja = (scalar >= 0x4E00 && scalar <= 0x9FFF) || (scalar >= 0x3400 && scalar <= 0x4DBF)
                guard isHanja else { i += 1; continue }

                var endIdx = i
                while endIdx + 1 < indices.count {
                    let nextChar = str[indices[endIdx + 1]]
                    let nextScalar = nextChar.unicodeScalars.first?.value ?? 0
                    let nextIsHanja = (nextScalar >= 0x4E00 && nextScalar <= 0x9FFF) || (nextScalar >= 0x3400 && nextScalar <= 0x4DBF)
                    guard nextIsHanja else { break }
                    endIdx += 1
                }

                let startRange = indices[i]..<str.index(after: indices[i])
                let endRange = indices[endIdx]..<str.index(after: indices[endIdx])
                let fullRange = indices[i]..<str.index(after: indices[endIdx])

                guard let startBox = try? candidate.boundingBox(for: startRange),
                      let endBox = try? candidate.boundingBox(for: endRange) else {
                    i = endIdx + 1; continue
                }
                let unionBox = startBox.boundingBox.union(endBox.boundingBox)

                let word = String(str[fullRange])
                var reading = ""
                var definitions: [String] = []
                for ch in word {
                    let r = db.readingForChar(String(ch)) ?? "?"
                    reading += r
                    if let def = db.definitionForChar(String(ch)) {
                        definitions.append("\(ch)(\(r)): \(def)")
                    }
                }

                guard !reading.isEmpty else { i = endIdx + 1; continue }

                items.append(OverlayItem(
                    character: word,
                    reading: reading,
                    definition: definitions.joined(separator: "\n"),
                    box: unionBox
                ))
                i = endIdx + 1
            }
        }
        return items
    }
}

// MARK: - 비디오 프레임 → OCR

extension OverlayViewModel: AVCaptureVideoDataOutputSampleBufferDelegate {
    nonisolated func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        Task { @MainActor in
            // 독음이 하나라도 표시 중이면 재스캔 안 함
            guard liveOCRActive, !isOCRProcessing, visibleReading == nil else { return }
            isOCRProcessing = true

            guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
                isOCRProcessing = false
                return
            }

            let w = CVPixelBufferGetWidth(pixelBuffer)
            let h = CVPixelBufferGetHeight(pixelBuffer)
            frameSize = CGSize(width: w, height: h)
            let aspect = CGFloat(w) / CGFloat(h)
            if self.cameraFrameAspect != aspect { self.cameraFrameAspect = aspect }

            let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
            let context = CIContext()
            guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else {
                isOCRProcessing = false
                return
            }

            lastFrameImage = UIImage(cgImage: cgImage)

            let request = VNRecognizeTextRequest { [weak self] request, _ in
                guard let self,
                      let observations = request.results as? [VNRecognizedTextObservation] else {
                    self?.isOCRProcessing = false
                    return
                }
                let items = self.buildOverlayItemsFromObservations(observations)
                Task { @MainActor in
                    self.overlayItems = items
                    self.isOCRProcessing = false
                }
            }
            request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
            request.recognitionLevel = .accurate

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])
        }
    }
}
