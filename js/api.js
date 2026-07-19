// API Client pour le frontend
const API = {
    baseUrl: 'http://localhost:5000/api',
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'include',
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Erreur serveur');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // Auth
    register(data) {
        return this.request('/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    login(email, password) {
        return this.request('/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },
    
    logout() {
        return this.request('/logout', {
            method: 'POST'
        });
    },
    
    me() {
        return this.request('/me');
    },
    
    // Profil
    updateProfil(data) {
        return this.request('/profil/update', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    updateInterets(interets) {
        return this.request('/profil/interets', {
            method: 'PUT',
            body: JSON.stringify({ interets })
        });
    },
    
    getInterets() {
        return this.request('/profil/interets');
    },
    
    // Swipe
    getProfils(ageMin = 18, ageMax = 99, limit = 20) {
        return this.request(`/swipe/profils?age_min=${ageMin}&age_max=${ageMax}&limit=${limit}`);
    },
    
    like(userId, type = 'like') {
        return this.request('/swipe/like', {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, type })
        });
    },
    
    // Matchs
    getMatchs() {
        return this.request('/matchs');
    },
    
    // Messages
    getMessages(matchId) {
        return this.request(`/messages/${matchId}`);
    },
    
    sendMessage(matchId, destinataireId, contenu) {
        return this.request('/messages/send', {
            method: 'POST',
            body: JSON.stringify({ match_id: matchId, destinataire_id: destinataireId, contenu })
        });
    },
    
    // Notifications
    getNotifications() {
        return this.request('/notifications');
    },
    
    markNotificationsRead() {
        return this.request('/notifications/read', {
            method: 'POST'
        });
    },
    
    // Search
    search(query) {
        return this.request(`/search?q=${encodeURIComponent(query)}`);
    },
    
    // Photos
    uploadPhoto(file) {
        const formData = new FormData();
        formData.append('photo', file);
        
        return this.request('/photo/upload', {
            method: 'POST',
            headers: {},
            body: formData
        });
    }
};

// Exemple d'utilisation dans vos pages HTML
// Remplacer les simulations par :

// Connexion
async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const result = await API.login(email, password);
        if (result.success) {
            window.location.href = 'dashboard.html';
        }
    } catch (error) {
        alert(error.message);
    }
}

// Inscription
async function handleRegister(data) {
    try {
        const result = await API.register(data);
        if (result.success) {
            window.location.href = 'dashboard.html';
        }
    } catch (error) {
        alert(error.message);
    }
}

// Swipe
async function loadProfils() {
    try {
        const result = await API.getProfils();
        if (result.success) {
            displayProfils(result.profils);
        }
    } catch (error) {
        console.error('Erreur chargement profils:', error);
    }
}

async function swipe(userId, type) {
    try {
        const result = await API.like(userId, type);
        if (result.match) {
            showMatchPopup();
        }
        loadNextProfil();
    } catch (error) {
        console.error('Erreur swipe:', error);
    }
}