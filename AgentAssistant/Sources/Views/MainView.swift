import SwiftUI

struct MainView: View {
    @EnvironmentObject var voiceManager: VoiceManager
    @EnvironmentObject var apiClient: APIClient
    @State private var scale: CGFloat = 1.0
    
    var body: some View {
        ZStack {
            // Background
            Color.white
            
            // Black circle
            Circle()
                .fill(.black)
                .frame(width: 40, height: 40)
                .scaleEffect(scale)
                .animation(.easeInOut(duration: 0.5), value: scale)
                .onTapGesture {
                    handleTap()
                }
        }
        .frame(width: 100, height: 100)
        .clipShape(RoundedRectangle(cornerRadius: 20))
        .shadow(radius: 10)
        .onChange(of: voiceManager.isListening) { isListening in
            withAnimation(.easeInOut(duration: 0.5).repeatForever()) {
                scale = isListening ? 1.2 : 1.0
            }
        }
    }
    
    private func handleTap() {
        if voiceManager.isListening {
            voiceManager.stopListening()
        } else {
            voiceManager.startListening()
        }
    }
}

#Preview {
    MainView()
        .environmentObject(VoiceManager())
        .environmentObject(APIClient())
} 