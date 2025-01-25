import SwiftUI
import AVFoundation

@main
struct AgentAssistantApp: App {
    @StateObject private var voiceManager = VoiceManager()
    @StateObject private var apiClient = APIClient()
    
    var body: some Scene {
        WindowGroup {
            MainView()
                .environmentObject(voiceManager)
                .environmentObject(apiClient)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 100, height: 100)
        .windowResizability(.contentSize)
    }
}

class VoiceManager: ObservableObject {
    @Published var isListening = false
    @Published var isProcessing = false
    private let speechRecognizer = SFSpeechRecognizer()
    private let synthesizer = AVSpeechSynthesizer()
    
    func startListening() {
        isListening = true
        // Implement speech recognition
    }
    
    func stopListening() {
        isListening = false
        // Stop recognition
    }
    
    func speak(_ text: String) {
        let utterance = AVSpeechUtterance(string: text)
        synthesizer.speak(utterance)
    }
}

class APIClient: ObservableObject {
    private let baseURL = "http://localhost:8000"
    
    func sendQuery(_ query: String) async throws -> String {
        // Implement API call
        return ""
    }
} 