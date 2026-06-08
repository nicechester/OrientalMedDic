import SwiftUI
import Vision
import PhotosUI
import Combine
import AVFoundation

struct OverlayReadingView: View {
    @StateObject private var viewModel = OverlayViewModel()
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedItem: OverlayItem?
    @State private var mode: OverlayMode = .camera

    enum OverlayMode {
        case camera
        case photo(UIImage)
    }

    var body: some View {
        NavigationStack {
            ZStack {
                if let capturedImage = viewModel.capturedImage {
                    staticOverlayView(image: capturedImage)
                } else {
                    switch mode {
                    case .camera:
                        liveCameraView
                    case .photo(let image):
                        staticOverlayView(image: image)
                    }
                }
            }
            .navigationTitle("독음 오버레이")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $selectedItem) { item in
                CharDetailSheet(item: item)
                    .presentationDetents([.medium])
            }
            .onChange(of: selectedPhoto) { _, item in
                guard let item else { return }
                Task {
                    if let data = try? await item.loadTransferable(type: Data.self),
                       let uiImage = UIImage(data: data) {
                        viewModel.processImage(uiImage)
                        mode = .photo(uiImage)
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

                // 실시간 오버레이
                ForEach(viewModel.overlayItems) { item in
                    let rect = convertVisionToScreen(
                        normalizedBox: item.box,
                        geoSize: geo.size
                    )
                    Rectangle()
                        .fill(Color.white.opacity(0.5))
                        .frame(width: rect.width, height: rect.height)
                        .position(x: rect.midX, y: rect.midY)

                    Text(item.reading)
                        .font(.system(size: max(rect.height * 0.6, 9)))
                        .foregroundStyle(.red)
                        .lineLimit(1)
                        .minimumScaleFactor(0.5)
                        .frame(width: rect.width, height: rect.height)
                        .position(x: rect.midX, y: rect.midY)
                        .onTapGesture {
                            viewModel.refineItem(item) { refined in
                                selectedItem = refined
                            }
                        }
                }

                // 하단 버튼들
                VStack {
                    Spacer()
                    HStack(spacing: 60) {
                        PhotosPicker(selection: $selectedPhoto, matching: .images) {
                            Image(systemName: "photo.on.rectangle")
                                .font(.system(size: 28))
                                .foregroundStyle(.white)
                                .frame(width: 50, height: 50)
                                .background(.ultraThinMaterial)
                                .clipShape(Circle())
                        }

                        Button(action: { viewModel.captureSnapshot() }) {
                            Circle()
                                .fill(.white)
                                .frame(width: 72, height: 72)
                                .overlay(Circle().stroke(.gray, lineWidth: 3))
                        }

                        Color.clear.frame(width: 50, height: 50)
                    }
                    .padding(.bottom, 120)
                }
            }
            .gesture(
                MagnifyGesture()
                    .onChanged { value in
                        let newZoom = lastCameraZoom * value.magnification
                        cameraZoom = newZoom
                        viewModel.setZoom(newZoom)
                    }
                    .onEnded { _ in
                        lastCameraZoom = cameraZoom
                    }
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
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)

                ForEach(viewModel.overlayItems) { item in
                    let rect = convertToScreen(normalizedBox: item.box, displayRect: displayRect)

                    Rectangle()
                        .fill(Color.white.opacity(0.5))
                        .frame(width: rect.width, height: rect.height)
                        .position(x: rect.midX, y: rect.midY)

                    Text(item.reading)
                        .font(.system(size: max(rect.height * 0.6, 9)))
                        .foregroundStyle(.red)
                        .lineLimit(1)
                        .minimumScaleFactor(0.5)
                        .frame(width: rect.width, height: rect.height)
                        .position(x: rect.midX, y: rect.midY)
                        .onTapGesture { selectedItem = item }
                }

                // 하단 버튼
                VStack {
                    Spacer()
                    Button(action: {
                        viewModel.capturedImage = nil
                        viewModel.overlayItems = []
                        mode = .camera
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "xmark")
                            Text("취소")
                        }
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: 120)
                        .frame(height: 44)
                        .background(Color.gray.opacity(0.6))
                        .cornerRadius(8)
                    }
                    .padding(.bottom, 120)
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
        }
        .ignoresSafeArea()
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
    @StateObject private var viewModel = CharDetailViewModel(character: "")

    init(item: OverlayItem) {
        self.item = item
        _viewModel = StateObject(wrappedValue: CharDetailViewModel(character: item.character))
    }

    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 16) {
                Text(item.character)
                    .font(.system(size: 36))
                Text(item.reading)
                    .font(.title2)
                    .foregroundStyle(.red)
            }

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    let wordResults = viewModel.results.filter { $0.category == "한자어" }
                    if !wordResults.isEmpty {
                        Section {
                            ForEach(wordResults, id: \.term) { result in
                                resultRow(result)
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
                            ForEach(herbalResults, id: \.term) { result in
                                resultRow(result)
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
                            ForEach(formulaResults, id: \.term) { result in
                                resultRow(result)
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
                            ForEach(acupointResults, id: \.term) { result in
                                resultRow(result)
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
                            ForEach(diseaseResults, id: \.term) { result in
                                resultRow(result)
                            }
                        } header: {
                            Text("병명 (질병)")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundStyle(.orange)
                        }
                    }

                    if !item.definition.isEmpty {
                        Section {
                            Text(item.definition)
                                .font(.callout)
                                .foregroundStyle(.secondary)
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

    private func resultRow(_ result: DBResult) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text(result.term)
                    .font(.headline)
                    .foregroundStyle(.black)
                Text(result.reading)
                    .font(.subheadline)
                    .foregroundStyle(.red)
            }
            Text(result.description)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(3)
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
    @Published var capturedImage: UIImage?
    @Published var isProcessing = false
    @Published var cameraFrameAspect: CGFloat = 3.0 / 4.0

    let session = AVCaptureSession()
    private var device: AVCaptureDevice?
    nonisolated(unsafe) private let db = DictionaryDB.shared

    // MARK: - 실시간 OCR (비디오 프레임 캡처 방식)

    private let videoOutput = AVCaptureVideoDataOutput()
    private let processingQueue = DispatchQueue(label: "ocr.processing")
    nonisolated(unsafe) private var liveOCRActive = false
    nonisolated(unsafe) private var isOCRProcessing = false
    nonisolated(unsafe) private var frameSize: CGSize = CGSize(width: 1080, height: 1920)
    nonisolated(unsafe) private var lastFrameImage: UIImage?

    func startLiveOCR() {
        liveOCRActive = true

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
        }

        updateVideoOutputRotation()
        DispatchQueue.global(qos: .userInitiated).async { self.session.startRunning() }
    }

    func stopLiveOCR() {
        liveOCRActive = false
        isOCRProcessing = true  // 현재 진행 중인 OCR도 중지
        DispatchQueue.global(qos: .userInitiated).async { self.session.stopRunning() }
    }

    func updateVideoOutputRotation() {
        guard let connection = videoOutput.connection(with: .video) else { return }
        let orientation = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }.first?.interfaceOrientation ?? .portrait
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

    func captureSnapshot() {
        stopLiveOCR()
        if let image = lastFrameImage {
            Task { @MainActor in
                capturedImage = image
            }
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

    // MARK: - 정적 이미지 처리

    func processImage(_ image: UIImage) {
        isProcessing = true
        let normalized = normalizeOrientation(image)
        guard let cgImage = normalized.cgImage else {
            isProcessing = false
            return
        }
        performOCR(on: cgImage) { [weak self] items in
            Task { @MainActor in
                self?.overlayItems = items
                self?.capturedImage = normalized
                self?.isProcessing = false
            }
        }
    }

    func reset() {
        capturedImage = nil
        overlayItems = []
    }

    /// 탭한 아이템의 bbox를 중국어 OCR로 재인식하여 정확도 향상
    func refineItem(_ item: OverlayItem, completion: @escaping (OverlayItem) -> Void) {
        guard let cgImage = lastFrameImage?.cgImage ?? capturedImage?.cgImage else {
            completion(item)
            return
        }

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { completion(item); return }

            let padX: CGFloat = 0.01
            let padY: CGFloat = 0.005
            let roi = CGRect(
                x: max(0, item.box.minX - padX),
                y: max(0, item.box.minY - padY),
                width: min(1 - max(0, item.box.minX - padX), item.box.width + padX * 2),
                height: min(1 - max(0, item.box.minY - padY), item.box.height + padY * 2)
            )

            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["zh-Hant", "zh-Hans"]
            request.usesLanguageCorrection = false
            request.regionOfInterest = roi

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])

            if let zhText = request.results?.first?.topCandidates(1).first?.string {
                let hanja = zhText.filter { ch in
                    let v = ch.unicodeScalars.first?.value ?? 0
                    return (v >= 0x4E00 && v <= 0x9FFF) || (v >= 0x3400 && v <= 0x4DBF) || (v >= 0xF900 && v <= 0xFAFF)
                }
                if !hanja.isEmpty {
                    var reading = ""
                    var definitions: [String] = []
                    for ch in hanja {
                        let r = self.db.readingForChar(String(ch)) ?? "?"
                        reading += r
                        if let def = self.db.definitionForChar(String(ch)) {
                            definitions.append("\(ch)(\(r)): \(def)")
                        }
                    }
                    let refined = OverlayItem(
                        character: hanja,
                        reading: reading,
                        definition: definitions.joined(separator: "\n"),
                        box: item.box
                    )
                    Task { @MainActor in completion(refined) }
                    return
                }
            }
            Task { @MainActor in completion(item) }
        }
    }

    // MARK: - OCR 처리

    private func performOCR(on cgImage: CGImage, completion: @escaping ([OverlayItem]) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { completion([]); return }
            let request = VNRecognizeTextRequest()
            request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
            request.recognitionLevel = .accurate

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])

            guard let observations = request.results else {
                completion([])
                return
            }
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

    private func normalizeOrientation(_ image: UIImage) -> UIImage {
        guard image.imageOrientation != .up else { return image }
        UIGraphicsBeginImageContextWithOptions(image.size, false, image.scale)
        image.draw(in: CGRect(origin: .zero, size: image.size))
        let normalized = UIGraphicsGetImageFromCurrentImageContext() ?? image
        UIGraphicsEndImageContext()
        return normalized
    }
}

// MARK: - 비디오 프레임 → OCR

extension OverlayViewModel: AVCaptureVideoDataOutputSampleBufferDelegate {
    nonisolated func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard liveOCRActive, !isOCRProcessing else { return }
        isOCRProcessing = true

        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            isOCRProcessing = false
            return
        }

        // 실제 프레임 크기 저장 (rotation 적용 후이므로 width < height)
        let w = CVPixelBufferGetWidth(pixelBuffer)
        let h = CVPixelBufferGetHeight(pixelBuffer)
        frameSize = CGSize(width: w, height: h)
        let aspect = CGFloat(w) / CGFloat(h)
        Task { @MainActor in
            if self.cameraFrameAspect != aspect {
                self.cameraFrameAspect = aspect
            }
        }

        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let context = CIContext()
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else {
            isOCRProcessing = false
            return
        }

        // 마지막 프레임 저장
        lastFrameImage = UIImage(cgImage: cgImage)

        let request = VNRecognizeTextRequest { [weak self] request, _ in
            guard let self,
                  let observations = request.results as? [VNRecognizedTextObservation] else {
                self?.isOCRProcessing = false
                return
            }
            // 실시간은 1-pass (한국어+중국어 동시) — 성능 우선
            let items = self.buildOverlayItemsFromObservations(observations)
            Task { @MainActor in
                self.overlayItems = items
                try? await Task.sleep(for: .seconds(3))
                self.isOCRProcessing = false
            }
        }
        request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
        request.recognitionLevel = .accurate

        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        try? handler.perform([request])
    }
}
