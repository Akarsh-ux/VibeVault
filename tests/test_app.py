import os
import sys
import io
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.db import query_db

class VibeVaultTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Test User 1
        self.user1_data = {
            'full_name': 'Test User One',
            'username': 'testuser1',
            'email': 'user1@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }
        # Test User 2 (for isolation testing)
        self.user2_data = {
            'full_name': 'Test User Two',
            'username': 'testuser2',
            'email': 'user2@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }

    def test_01_landing_page(self):
        """Test public landing page loads properly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Vibe Vault', response.data)
        self.assertIn(b'Get Started', response.data)

    def test_02_registration_and_validation(self):
        """Test user registration, duplicate prevention, and password checks."""
        # Valid registration
        res = self.client.post('/api/register', json=self.user1_data)
        self.assertIn(res.status_code, [201, 409]) # 201 created or 409 if already registered
        
        # Duplicate registration check
        res_dup = self.client.post('/api/register', json=self.user1_data)
        self.assertEqual(res_dup.status_code, 409)
        
        # Mismatched password
        bad_data = dict(self.user1_data)
        bad_data['username'] = 'mismatch_user'
        bad_data['email'] = 'mismatch@test.com'
        bad_data['confirm_password'] = 'wrongpass'
        res_bad = self.client.post('/api/register', json=bad_data)
        self.assertEqual(res_bad.status_code, 400)

    def test_03_login_and_logout(self):
        """Test login, authentication session, and logout."""
        # Ensure user2 is registered
        self.client.post('/api/register', json=self.user2_data)

        # Invalid login
        res_fail = self.client.post('/api/login', json={'login_input': 'testuser2', 'password': 'wrongpassword'})
        self.assertEqual(res_fail.status_code, 401)

        # Valid login
        res_success = self.client.post('/api/login', json={'login_input': 'testuser2', 'password': 'password123'})
        self.assertEqual(res_success.status_code, 200)
        self.assertTrue(res_success.json['success'])

        # Protected route access with active session
        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        # Logout
        res_logout = self.client.post('/api/logout')
        self.assertEqual(res_logout.status_code, 200)

    def test_04_auth_protection(self):
        """Test protected routes redirect or return 401 when not logged in."""
        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 302) # Redirect to login

        res_api = self.client.get('/api/songs')
        self.assertEqual(res_api.status_code, 401)

    def test_05_song_upload_and_management(self):
        """Test song uploading, metadata, and listing."""
        # Login user1
        self.client.post('/api/login', json={'login_input': 'testuser1', 'password': 'password123'})

        # Upload dummy WAV file
        dummy_wav = io.BytesIO(b'RIFF....WAVEfmt ....data....')
        data = {
            'audio_file': (dummy_wav, 'test_sample.wav'),
            'title': 'Test Audio Track',
            'artist': 'Test Band',
            'album': 'Test Album',
            'genre': 'Rock',
            'duration': '180'
        }
        res_upload = self.client.post('/api/songs', data=data, content_type='multipart/form-data')
        self.assertEqual(res_upload.status_code, 201)
        song_id = res_upload.json['song']['id']

        # Get all songs
        res_list = self.client.get('/api/songs')
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(any(s['id'] == song_id for s in res_list.json['songs']))

        # Update song metadata
        res_update = self.client.put(f'/api/songs/{song_id}', data={'title': 'Updated Track Title', 'artist': 'Updated Band'})
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json['song']['title'], 'Updated Track Title')

    def test_06_playlist_crud_and_reorder(self):
        """Test playlist creation, adding songs, duplicate checks, and deletion."""
        self.client.post('/api/login', json={'login_input': 'testuser1', 'password': 'password123'})

        # Create Playlist
        res_create = self.client.post('/api/playlists', json={'name': 'Focus Work Mix', 'description': 'Deep concentration'})
        self.assertEqual(res_create.status_code, 201)
        playlist_id = res_create.json['playlist']['id']

        # Fetch songs to add
        res_songs = self.client.get('/api/songs')
        if res_songs.json['songs']:
            song_id = res_songs.json['songs'][0]['id']

            # Add song to playlist
            res_add = self.client.post(f'/api/playlists/{playlist_id}/songs', json={'song_id': song_id})
            self.assertEqual(res_add.status_code, 200)

            # Try adding duplicate
            res_dup = self.client.post(f'/api/playlists/{playlist_id}/songs', json={'song_id': song_id})
            self.assertEqual(res_dup.status_code, 409)

            # Check playlist contents
            res_detail = self.client.get(f'/api/playlists/{playlist_id}')
            self.assertEqual(res_detail.status_code, 200)
            self.assertEqual(len(res_detail.json['songs']), 1)

            # Remove song
            res_remove = self.client.delete(f'/api/playlists/{playlist_id}/songs/{song_id}')
            self.assertEqual(res_remove.status_code, 200)

        # Delete playlist
        res_del = self.client.delete(f'/api/playlists/{playlist_id}')
        self.assertEqual(res_del.status_code, 200)

    def test_07_favorites_and_history(self):
        """Test toggling favorites and playback tracking."""
        self.client.post('/api/login', json={'login_input': 'testuser1', 'password': 'password123'})

        res_songs = self.client.get('/api/songs')
        if res_songs.json['songs']:
            song_id = res_songs.json['songs'][0]['id']

            # Toggle Favorite ON
            res_fav1 = self.client.post(f'/api/favorites/toggle/{song_id}')
            self.assertEqual(res_fav1.status_code, 200)
            self.assertTrue(res_fav1.json['is_favorite'])

            # Verify in Favorites list
            res_favs = self.client.get('/api/favorites')
            self.assertTrue(any(s['id'] == song_id for s in res_favs.json['songs']))

            # Record Playback
            res_play = self.client.post('/api/recently-played', json={'song_id': song_id})
            self.assertEqual(res_play.status_code, 200)

            # Verify in Recently Played
            res_rec = self.client.get('/api/recently-played')
            self.assertTrue(any(s['id'] == song_id for s in res_rec.json['songs']))

    def test_08_search_api(self):
        """Test global multi-entity search."""
        self.client.post('/api/login', json={'login_input': 'testuser1', 'password': 'password123'})

        res_search = self.client.get('/api/search?q=Track')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn('songs', res_search.json['results'])
        self.assertIn('playlists', res_search.json['results'])

    def test_09_user_data_isolation(self):
        """Critical test: verify User B cannot view or modify User A's songs or playlists."""
        # Login User 1 and create a private playlist & song
        self.client.post('/api/login', json={'login_input': 'testuser1', 'password': 'password123'})
        res_pl = self.client.post('/api/playlists', json={'name': 'User 1 Secret Playlist', 'description': 'Private'})
        u1_playlist_id = res_pl.json['playlist']['id']

        res_song = self.client.post('/api/songs', data={
            'audio_file': (io.BytesIO(b'RIFF....WAVEfmt ....data....'), 'u1_song.wav'),
            'title': 'User 1 Secret Song'
        }, content_type='multipart/form-data')
        u1_song_id = res_song.json['song']['id']

        # Switch to User 2
        self.client.post('/api/logout')
        self.client.post('/api/login', json={'login_input': 'testuser2', 'password': 'password123'})

        # User 2 attempting to view User 1's playlist
        res_view_pl = self.client.get(f'/api/playlists/{u1_playlist_id}')
        self.assertEqual(res_view_pl.status_code, 404)

        # User 2 attempting to delete User 1's playlist
        res_del_pl = self.client.delete(f'/api/playlists/{u1_playlist_id}')
        self.assertEqual(res_del_pl.status_code, 404)

        # User 2 attempting to delete User 1's song
        res_del_song = self.client.delete(f'/api/songs/{u1_song_id}')
        self.assertEqual(res_del_song.status_code, 404)

if __name__ == '__main__':
    unittest.main()
