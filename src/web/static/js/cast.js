/**
 * Google Cast SDK Integration
 *
 * CAST-01: Cast button appears when devices available
 * CAST-02: User can connect to Chromecast/Smart TV devices
 * CAST-05: Cast session state persists across navigation
 */

class CastManager {
    constructor() {
        this.session = null;
        this.sessionListener = null;
        this.currentPostId = null;
        this.postQueue = [];
        this.queueIndex = -1;

        // Initialize Cast API
        this.initializeCastApi();
    }

    initializeCastApi() {
        // Use the default media receiver ID for development
        // Replace with custom app ID for production
        const applicationID = 'CC1AD845'; // Default media receiver

        const sessionRequest = new chrome.cast.SessionRequest(applicationID);
        const apiConfig = new chrome.cast.ApiConfig(
            sessionRequest,
            this.sessionListener.bind(this),
            this.receiverListener.bind(this)
        );

        chrome.cast.initialize(
            apiConfig,
            this.onInitSuccess.bind(this),
            this.onError.bind(this)
        );
    }

    onInitSuccess() {
        console.log('Cast API initialized successfully');
        this.updateCastButton();
    }

    onError(error) {
        console.error('Cast API error:', error);
    }

    sessionListener(session) {
        this.session = session;
        this.session.addMessageListener(
            'urn:x-cast:com.bookmarked.posts',
            this.onMessage.bind(this)
        );
        this.updateCastButton();
    }

    receiverListener(availability) {
        if (availability === 'available') {
            document.getElementById('cast-button')?.classList.remove('hidden');
        } else {
            document.getElementById('cast-button')?.classList.add('hidden');
        }
    }

    updateCastButton() {
        const button = document.getElementById('cast-button');
        if (!button) return;

        if (this.session) {
            button.innerHTML = '<svg class="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24"><path d="M1 18v3h3c0-1.66-1.34-3-3-3zm0-4v2c2.76 0 5 2.24 5 5h2c0-3.87-3.13-7-7-7zm0-4v2c4.97 0 9 4.03 9 9h2c0-6.08-4.93-11-11-11z"/></svg>';
            button.title = 'Connected to ' + this.session.receiver.friendlyName;
        } else {
            button.innerHTML = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M1 18v3h3c0-1.66-1.34-3-3-3zm0-4v2c2.76 0 5 2.24 5 5h2c0-3.87-3.13-7-7-7zm0-4v2c4.97 0 9 4.03 9 9h2c0-6.08-4.93-11-11-11z"/></svg>';
            button.title = 'Cast to device';
        }
    }

    requestSession() {
        chrome.cast.requestSession(
            (session) => {
                this.session = session;
                this.session.addMessageListener(
                    'urn:x-cast:com.bookmarked.posts',
                    this.onMessage.bind(this)
                );
                this.updateCastButton();
            },
            (error) => {
                console.error('Session request error:', error);
            }
        );
    }

    disconnect() {
        if (this.session) {
            this.session.stop(
                () => {
                    this.session = null;
                    this.updateCastButton();
                    this.hideMiniController();
                },
                (error) => {
                    console.error('Disconnect error:', error);
                }
            );
        }
    }

    onMessage(namespace, message) {
        try {
            const data = JSON.parse(message);
            if (data.type === 'ACKNOWLEDGE') {
                console.log('Receiver acknowledged:', data.postId);
                this.hideLoadingSpinner();
            }
        } catch (e) {
            console.error('Message parse error:', e);
        }
    }

    async loadPost(postId) {
        if (!this.session) {
            console.error('No active Cast session');
            return;
        }

        this.showLoadingSpinner();
        this.currentPostId = postId;

        try {
            // Fetch post data from API
            const response = await fetch(`/api/posts/${postId}`);
            const post = await response.json();

            // Build message payload with embedded post data for retweets/quotes
            // CAST-06, CAST-07, CAST-08: Include post_type and embedded_post for TV rendering
            const message = {
                type: 'LOAD_POST',
                postId: postId,
                post: {
                    x_post_id: post.x_post_id,
                    author_username: post.author_username,
                    author_display_name: post.author_display_name,
                    text: post.text,
                    created_at: post.created_at,
                    media_urls: post.media_urls,
                    topics: post.topics || [],
                    post_type: post.post_type || 'original',
                    embedded_post: post.embedded_post || null
                }
            };

            // Log embedded post data for debugging retweets/quotes
            if (post.embedded_post) {
                console.log('Casting post with embedded content:', {
                    post_type: post.post_type,
                    embedded_author: post.embedded_post.author_username,
                    embedded_available: post.embedded_post.available
                });
            }

            this.session.sendMessage(
                'urn:x-cast:com.bookmarked.posts',
                JSON.stringify(message),
                () => console.log('Post sent to receiver'),
                (error) => console.error('Send error:', error)
            );
        } catch (error) {
            console.error('Load post error:', error);
            this.hideLoadingSpinner();
        }
    }

    async nextPost() {
        if (this.queueIndex < this.postQueue.length - 1) {
            this.queueIndex++;
            await this.loadPost(this.postQueue[this.queueIndex]);
        }
    }

    async previousPost() {
        if (this.queueIndex > 0) {
            this.queueIndex--;
            await this.loadPost(this.postQueue[this.queueIndex]);
        }
    }

    setPostQueue(posts) {
        this.postQueue = posts;
        this.queueIndex = -1;
    }

    showLoadingSpinner() {
        const spinner = document.getElementById('cast-loading');
        if (spinner) spinner.classList.remove('hidden');
    }

    hideLoadingSpinner() {
        const spinner = document.getElementById('cast-loading');
        if (spinner) spinner.classList.add('hidden');
    }

    showMiniController(postTitle) {
        const controller = document.getElementById('mini-controller');
        const titleEl = document.getElementById('controller-title');
        if (controller && titleEl) {
            titleEl.textContent = postTitle || 'Now Casting';
            controller.classList.remove('hidden');
        }
    }

    hideMiniController() {
        const controller = document.getElementById('mini-controller');
        if (controller) {
            controller.classList.add('hidden');
        }
    }
}

// Global instance
window.CastManager = null;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.CastManager = new CastManager();
});

// Re-attach to session on navigation
window.addEventListener('load', () => {
    if (window.CastManager && window.CastManager.session) {
        window.CastManager.updateCastButton();
    }
});