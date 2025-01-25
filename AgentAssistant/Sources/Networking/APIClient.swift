import Foundation

class APIClient: ObservableObject {
    private let baseURL = "http://localhost:8000"
    @Published var isConnected = false
    
    struct APIError: Error {
        let message: String
    }
    
    struct QueryResponse: Codable {
        let status: String
        let response: String
    }
    
    func checkConnection() async {
        do {
            let url = URL(string: "\(baseURL)/")!
            let (_, response) = try await URLSession.shared.data(from: url)
            
            DispatchQueue.main.async {
                self.isConnected = (response as? HTTPURLResponse)?.statusCode == 200
            }
        } catch {
            DispatchQueue.main.async {
                self.isConnected = false
            }
        }
    }
    
    func sendQuery(_ query: String) async throws -> String {
        guard let url = URL(string: "\(baseURL)/query") else {
            throw APIError(message: "Invalid URL")
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["query": query]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response")
        }
        
        guard httpResponse.statusCode == 200 else {
            throw APIError(message: "Server error: \(httpResponse.statusCode)")
        }
        
        let queryResponse = try JSONDecoder().decode(QueryResponse.self, from: data)
        return queryResponse.response
    }
    
    func enableVoice() async throws {
        let url = URL(string: "\(baseURL)/voice/enable")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to enable voice")
        }
    }
    
    func getVoiceStatus() async throws -> Bool {
        let url = URL(string: "\(baseURL)/voice/status")!
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to get voice status")
        }
        
        struct VoiceStatus: Codable {
            let enabled: Bool
        }
        
        let status = try JSONDecoder().decode(VoiceStatus.self, from: data)
        return status.enabled
    }
} 