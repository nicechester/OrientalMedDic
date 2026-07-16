import CoreImage
import CoreImage.CIFilterBuiltins

enum ImagePreprocessor {
    /// Preprocess low-resolution images for better OCR accuracy
    /// - Parameters:
    ///   - cgImage: The image to preprocess
    ///   - scaleFactor: Upscaling factor (1.5-3.0 recommended, default 2.0)
    ///   - contrastBoost: Contrast multiplier (1.0-3.0 recommended, default 2.5)
    /// - Returns: Preprocessed CGImage or nil if preprocessing fails
    static func preprocess(
        _ cgImage: CGImage,
        scaleFactor: CGFloat = 2.0,
        contrastBoost: CGFloat = 2.5
    ) -> CGImage? {
        let ciImage = CIImage(cgImage: cgImage)

        // 1. Upscale with Lanczos (preserves edges better than bilinear)
        guard let upscaleFilter = CIFilter(name: "CILanczosScaleTransform") else {
            return nil
        }
        upscaleFilter.setValue(ciImage, forKey: kCIInputImageKey)
        upscaleFilter.setValue(scaleFactor, forKey: kCIInputScaleKey)
        upscaleFilter.setValue(1.0, forKey: kCIInputAspectRatioKey)

        guard let upscaledImage = upscaleFilter.outputImage else {
            return nil
        }

        // 2. Boost contrast and remove color (grayscale)
        let contrastFilter = CIFilter.colorControls()
        contrastFilter.inputImage = upscaledImage
        contrastFilter.contrast = Float(contrastBoost)
        contrastFilter.saturation = 0.0 // Remove color artifacts

        guard let processedImage = contrastFilter.outputImage else {
            return nil
        }

        // 3. Render to CGImage
        let context = CIContext(options: [.useSoftwareRenderer: false])
        return context.createCGImage(processedImage, from: processedImage.extent)
    }
}
