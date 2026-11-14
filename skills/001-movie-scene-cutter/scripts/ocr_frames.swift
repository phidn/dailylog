#!/usr/bin/env swift
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    print("Usage: ocr_frames.swift <directory_with_jpgs>")
    exit(1)
}

let dirPath = CommandLine.arguments[1]
let fm = FileManager.default

guard let files = try? fm.contentsOfDirectory(atPath: dirPath) else {
    print("Could not list directory: \(dirPath)")
    exit(1)
}

let imageFiles = files.filter { $0.hasSuffix(".jpg") || $0.hasSuffix(".png") }.sorted()

for file in imageFiles {
    let filePath = "\(dirPath)/\(file)"
    guard let img = NSImage(contentsOfFile: filePath),
          let cgImg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    
    let request = VNRecognizeTextRequest()
    request.recognitionLanguages = ["vi-VN", "zh-Hans", "en-US"]
    request.recognitionLevel = .accurate
    let handler = VNImageRequestHandler(cgImage: cgImg, options: [:])
    try? handler.perform([request])
    
    if let results = request.results {
        let texts = results.compactMap { $0.topCandidates(1).first?.string }
        let textJoined = texts.joined(separator: " | ")
        if !textJoined.isEmpty {
            print("[\(file)] \(textJoined)")
        }
    }
}
