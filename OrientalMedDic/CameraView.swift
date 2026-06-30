import SwiftUI
import AVFoundation
import Vision
import Combine
import PhotosUI
import CoreMotion
import os

struct CameraView: View {
    @ObservedObject var viewModel: CameraViewModel
    @State private var resultText: String = ""
    @State private var zoomLevel: CGFloat = 1.0
    @State private var lastZoomLevel: CGFloat = 1.0
    @State private var selectedPhoto: PhotosPickerItem?

    var body: some View {
        NavigationStack {
            Group {
                if let image = viewModel.capturedImage {
                    // 2단계: 크롭 모드
                    CropView(image: image, onCrop: { croppedImage in
                        viewModel.performOCR(on: croppedImage)
                    }, onRetake: {
                        viewModel.retake()
                    })
                } else {
                    // 1단계: 카메라 모드
                    cameraLayer
                }
            }
            .navigationTitle("한자 스캔")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $viewModel.showResult) {
                ScanResultView(inputText: resultText)
            }
            .onChange(of: viewModel.recognizedText) { _, newValue in
                if let text = newValue {
                    resultText = text
                    viewModel.recognizedText = nil
                    viewModel.showResult = true
                }
            }
        }
    }

    private var cameraLayer: some View {
        GeometryReader { geo in
            ZStack {
                CameraPreview(session: viewModel.session)
                    .simultaneousGesture(
                        MagnifyGesture()
                            .onChanged { value in
                                let newZoom = lastZoomLevel * value.magnification
                                zoomLevel = newZoom
                                viewModel.setZoom(newZoom)
                            }
                            .onEnded { _ in
                                lastZoomLevel = zoomLevel
                            }
                    )

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

                        Button(action: { viewModel.capture() }) {
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
        }
        .ignoresSafeArea()
        .onAppear { viewModel.startSession() }
        .onDisappear { viewModel.stopSession() }
        .onChange(of: selectedPhoto) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self),
                   let uiImage = UIImage(data: data) {
                    viewModel.capturedImage = uiImage
                }
                selectedPhoto = nil
            }
        }
    }
}

// MARK: - Crop View

struct CropView: View {
    let image: UIImage
    let onCrop: (CGImage) -> Void
    let onRetake: () -> Void

    @State private var roiRect = CGRect.zero
    @State private var dragStart: CGRect = .zero
    @State private var zoomLevel: CGFloat = 1.0
    @State private var lastZoomLevel: CGFloat = 1.0

    var body: some View {
        GeometryReader { geo in
            let geoSize = geo.size
            ZStack {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .scaleEffect(zoomLevel)
                    .simultaneousGesture(
                        MagnifyGesture()
                            .onChanged { value in
                                let newZoom = lastZoomLevel * value.magnification
                                zoomLevel = newZoom
                            }
                            .onEnded { _ in
                                lastZoomLevel = zoomLevel
                            }
                    )

                if roiRect != .zero {
                    // 어두운 오버레이
                    Canvas { context, size in
                        context.fill(Path(CGRect(origin: .zero, size: size)), with: .color(.black.opacity(0.5)))
                        context.blendMode = .destinationOut
                        context.fill(Path(roiRect), with: .color(.white))
                    }
                    .compositingGroup()
                    .allowsHitTesting(false)

                    // 노란 테두리
                    Rectangle()
                        .stroke(.yellow, lineWidth: 2)
                        .frame(width: roiRect.width, height: roiRect.height)
                        .position(x: roiRect.midX, y: roiRect.midY)
                        .allowsHitTesting(false)

                    // 이동 제스처
                    Rectangle()
                        .fill(.clear)
                        .contentShape(Rectangle())
                        .frame(width: max(roiRect.width - 60, 50), height: max(roiRect.height - 60, 50))
                        .position(x: roiRect.midX, y: roiRect.midY)
                        .gesture(
                            DragGesture()
                                .onChanged { value in
                                    if dragStart == .zero { dragStart = roiRect }
                                    roiRect.origin.x = dragStart.origin.x + value.translation.width
                                    roiRect.origin.y = dragStart.origin.y + value.translation.height
                                }
                                .onEnded { _ in dragStart = .zero }
                        )

                    // 코너 핸들
                    cornerHandle(.topLeft)
                    cornerHandle(.topRight)
                    cornerHandle(.bottomLeft)
                    cornerHandle(.bottomRight)
                }

                // 하단 버튼
                VStack {
                    Spacer()
                    HStack(spacing: 40) {
                        Button(action: onRetake) {
                            Label("취소", systemImage: "xmark")
                                .font(.headline)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 10)
                                .background(.ultraThinMaterial)
                                .cornerRadius(20)
                        }

                        Button(action: { cropAndRecognize(geoSize: geoSize) }) {
                            Label("인식", systemImage: "text.viewfinder")
                                .font(.headline)
                                .padding(.horizontal, 24)
                                .padding(.vertical, 10)
                                .background(.blue)
                                .foregroundStyle(.white)
                                .cornerRadius(20)
                        }
                    }
                    .padding(.bottom, 120)
                }
            }
            .onAppear { resetROI(for: geoSize) }
            .onChange(of: geoSize) { _, newSize in resetROI(for: newSize) }
        }
        .ignoresSafeArea()
    }

    private func resetROI(for size: CGSize) {
        let w = size.width * 0.85
        let h = size.height * 0.6
        roiRect = CGRect(
            x: (size.width - w) / 2,
            y: (size.height - h) / 2,
            width: w,
            height: h
        )
    }

    enum Corner { case topLeft, topRight, bottomLeft, bottomRight }

    private func cornerPosition(_ corner: Corner) -> CGPoint {
        switch corner {
        case .topLeft: return CGPoint(x: roiRect.minX, y: roiRect.minY)
        case .topRight: return CGPoint(x: roiRect.maxX, y: roiRect.minY)
        case .bottomLeft: return CGPoint(x: roiRect.minX, y: roiRect.maxY)
        case .bottomRight: return CGPoint(x: roiRect.maxX, y: roiRect.maxY)
        }
    }

    private func cornerHandle(_ corner: Corner) -> some View {
        Circle()
            .fill(.yellow)
            .frame(width: 30, height: 30)
            .contentShape(Rectangle().size(width: 60, height: 60))
            .position(cornerPosition(corner))
            .gesture(
                DragGesture()
                    .onChanged { value in
                        if dragStart == .zero { dragStart = roiRect }
                        resize(corner: corner, translation: value.translation)
                    }
                    .onEnded { _ in dragStart = .zero }
            )
    }

    private func resize(corner: Corner, translation: CGSize) {
        let minSize: CGFloat = 20
        var r = dragStart
        switch corner {
        case .topLeft:
            r.origin.x += translation.width
            r.origin.y += translation.height
            r.size.width -= translation.width
            r.size.height -= translation.height
        case .topRight:
            r.origin.y += translation.height
            r.size.width += translation.width
            r.size.height -= translation.height
        case .bottomLeft:
            r.origin.x += translation.width
            r.size.width -= translation.width
            r.size.height += translation.height
        case .bottomRight:
            r.size.width += translation.width
            r.size.height += translation.height
        }
        if r.width >= minSize && r.height >= minSize {
            roiRect = r
        }
    }

    private func cropAndRecognize(geoSize: CGSize) {
        // orientation 적용된 이미지로 정규화
        let normalizedImage = normalizeOrientation(image)
        guard let cgImage = normalizedImage.cgImage else { return }

        let imgW = CGFloat(cgImage.width)
        let imgH = CGFloat(cgImage.height)

        // scaledToFit 표시 영역 계산
        let imageAspect = imgW / imgH
        let screenAspect = geoSize.width / geoSize.height

        let displayRect: CGRect
        if imageAspect > screenAspect {
            let displayW = geoSize.width
            let displayH = displayW / imageAspect
            let y = (geoSize.height - displayH) / 2
            displayRect = CGRect(x: 0, y: y, width: displayW, height: displayH)
        } else {
            let displayH = geoSize.height
            let displayW = displayH * imageAspect
            let x = (geoSize.width - displayW) / 2
            displayRect = CGRect(x: x, y: 0, width: displayW, height: displayH)
        }

        // ROI를 이미지 픽셀 좌표로 변환
        let scaleX = imgW / displayRect.width
        let scaleY = imgH / displayRect.height

        let cropX = (roiRect.origin.x - displayRect.origin.x) * scaleX
        let cropY = (roiRect.origin.y - displayRect.origin.y) * scaleY
        let cropW = roiRect.width * scaleX
        let cropH = roiRect.height * scaleY

        let cropRect = CGRect(x: max(cropX, 0), y: max(cropY, 0),
                              width: min(cropW, imgW), height: min(cropH, imgH))

        if let cropped = cgImage.cropping(to: cropRect) {
            onCrop(cropped)
        }
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

// MARK: - Camera Preview

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewUIView {
        let view = PreviewUIView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: PreviewUIView, context: Context) {}

    class PreviewUIView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
        override func layoutSubviews() {
            super.layoutSubviews()
            previewLayer.frame = bounds
            guard let connection = previewLayer.connection else { return }
            let windowScene = window?.windowScene
            let orientation = windowScene?.interfaceOrientation ?? .portrait
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

// MARK: - Camera ViewModel

@MainActor
class CameraViewModel: NSObject, ObservableObject {
    @Published var recognizedText: String?
    @Published var capturedImage: UIImage?
    @Published var showResult = false
    @Published var detectedLandscapeText = false

    let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private let videoOutput = AVCaptureVideoDataOutput()
    private var device: AVCaptureDevice?
    private let motionManager = CMMotionManager()
    private var deviceOrientation: UIDeviceOrientation = .portrait
    private var textDetectionTimer: Timer?
    private let textDetectionQueue = DispatchQueue(label: "textDetection", qos: .utility)

    func startSession() {
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device) else { return }

        self.device = device
        session.beginConfiguration()
        if session.canAddInput(input) { session.addInput(input) }
        if session.canAddOutput(output) { session.addOutput(output) }
        // Add video output for text orientation detection
        videoOutput.setSampleBufferDelegate(self, queue: textDetectionQueue)
        videoOutput.alwaysDiscardsLateVideoFrames = true
        if session.canAddOutput(videoOutput) { session.addOutput(videoOutput) }
        session.commitConfiguration()

        startMotionUpdates()
        startTextOrientationDetection()

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.session.startRunning()
        }
    }

    func stopSession() {
        stopMotionUpdates()
        textDetectionTimer?.invalidate()
        textDetectionTimer = nil
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.session.stopRunning()
        }
    }

    // MARK: - Motion-based orientation (reliable for photo capture)

    private func startMotionUpdates() {
        motionManager.accelerometerUpdateInterval = 0.2
        motionManager.startAccelerometerUpdates(to: .main) { [weak self] data, _ in
            guard let data = data else { return }
            let x = data.acceleration.x
            let y = data.acceleration.y
            if abs(x) > abs(y) {
                self?.deviceOrientation = x > 0 ? .landscapeRight : .landscapeLeft
            } else {
                self?.deviceOrientation = y > 0 ? .portraitUpsideDown : .portrait
            }
        }
    }

    private func stopMotionUpdates() {
        motionManager.stopAccelerometerUpdates()
    }

    // MARK: - Text orientation detection

    private let _shouldProcessFrame = OSAllocatedUnfairLock(initialState: false)

    private func startTextOrientationDetection() {
        textDetectionTimer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { [weak self] _ in
            self?._shouldProcessFrame.withLock { $0 = true }
        }
    }

    nonisolated func detectTextOrientation(in sampleBuffer: CMSampleBuffer) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        let request = VNRecognizeTextRequest { [weak self] request, _ in
            guard let results = request.results as? [VNRecognizedTextObservation], results.count >= 3 else { return }

            // Check if text bounding boxes are wider than tall (landscape text in portrait frame)
            var landscapeCount = 0
            for obs in results.prefix(10) {
                let box = obs.boundingBox
                if box.width > box.height * 2.0 {
                    landscapeCount += 1
                }
            }

            let isLandscapeText = landscapeCount > results.prefix(10).count / 2

            Task { @MainActor in
                guard let self = self else { return }
                if self.detectedLandscapeText != isLandscapeText {
                    self.detectedLandscapeText = isLandscapeText
                    if isLandscapeText {
                        self.requestLandscapeRotation()
                    }
                }
            }
        }
        request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
        request.recognitionLevel = .fast
        request.minimumTextHeight = 0.02

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up, options: [:])
        try? handler.perform([request])
    }

    private func requestLandscapeRotation() {
        // Force landscape orientation when landscape text detected
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene else { return }
        let currentOrientation = windowScene.interfaceOrientation
        guard currentOrientation.isPortrait else { return }

        let geometryPreferences = UIWindowScene.GeometryPreferences.iOS(interfaceOrientations: .landscape)
        windowScene.requestGeometryUpdate(geometryPreferences) { _ in }

        // Also set the preferred orientation via the supported orientations
        if #available(iOS 16.0, *) {
            UIViewController.attemptRotationToDeviceOrientation()
        }
    }

    func setZoom(_ factor: CGFloat) {
        guard let device = device else { return }
        let zoom = max(1.0, min(factor, device.activeFormat.videoMaxZoomFactor, 10.0))
        do {
            try device.lockForConfiguration()
            device.videoZoomFactor = zoom
            device.unlockForConfiguration()
        } catch {}
    }

    func capture() {
        let settings = AVCapturePhotoSettings()
        // Use accelerometer-based orientation for reliable rotation
        if let connection = output.connection(with: .video) {
            let angle: CGFloat = switch deviceOrientation {
            case .landscapeRight: 0
            case .landscapeLeft: 180
            case .portraitUpsideDown: 270
            default: 90
            }
            if connection.isVideoRotationAngleSupported(angle) {
                connection.videoRotationAngle = angle
            }
        }
        output.capturePhoto(with: settings, delegate: self)
    }

    func retake() {
        capturedImage = nil
        recognizedText = nil
    }

    func performOCR(on image: CGImage) {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let request = VNRecognizeTextRequest()
            request.recognitionLanguages = ["zh-Hant", "zh-Hans", "ko"]
            request.recognitionLevel = .accurate

            let handler = VNImageRequestHandler(cgImage: image, options: [:])
            try? handler.perform([request])

            let text = (request.results ?? []).compactMap {
                $0.topCandidates(1).first?.string
            }.joined(separator: "\n")

            let readingText = DictionaryDB.shared.generateReadingText(for: text)

            Task { @MainActor in
                self?.recognizedText = readingText.isEmpty ? nil : readingText
            }
        }
    }

}

extension CameraViewModel: AVCapturePhotoCaptureDelegate {
    nonisolated func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        guard let data = photo.fileDataRepresentation(),
              let uiImage = UIImage(data: data) else { return }

        Task { @MainActor in
            capturedImage = uiImage
        }
    }
}

extension CameraViewModel: AVCaptureVideoDataOutputSampleBufferDelegate {
    nonisolated func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        let shouldProcess = _shouldProcessFrame.withLock { val -> Bool in
            guard val else { return false }
            val = false
            return true
        }
        guard shouldProcess else { return }
        detectTextOrientation(in: sampleBuffer)
    }
}
