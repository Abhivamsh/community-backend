from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import Post, Comment, Like, KarmaTransaction


class LeaderboardTestCase(TestCase):
    """
    Test case for the 24-hour leaderboard calculation.
    This demonstrates that karma is calculated dynamically from transactions.
    """
    
    def setUp(self):
        """Create test users and content."""
        self.user1 = User.objects.create_user(username='alice', password='test123')
        self.user2 = User.objects.create_user(username='bob', password='test123')
        self.user3 = User.objects.create_user(username='charlie', password='test123')
        self.liker = User.objects.create_user(username='liker', password='test123')
    
    def test_leaderboard_calculation_24h(self):
        """
        Test that the leaderboard correctly calculates karma earned in the last 24 hours.
        """
        # User1 creates a post and gets 2 likes (10 karma)
        post1 = Post.objects.create(author=self.user1, content="Test post 1")
        like1 = Like.objects.create(user=self.user2, post=post1)
        like2 = Like.objects.create(user=self.user3, post=post1)
        
        # User2 creates a comment and gets 3 likes (3 karma)
        comment1 = Comment.objects.create(post=post1, author=self.user2, content="Test comment")
        like3 = Like.objects.create(user=self.user1, comment=comment1)
        like4 = Like.objects.create(user=self.user3, comment=comment1)
        like5 = Like.objects.create(user=self.liker, comment=comment1)
        
        # User3 creates a post (no likes, 0 karma)
        post2 = Post.objects.create(author=self.user3, content="Test post 2")
        
        # Get leaderboard
        leaderboard = KarmaTransaction.get_leaderboard(hours=24, limit=5)
        
        # Verify results
        self.assertEqual(len(leaderboard), 2)  # Only users with karma appear
        
        # User1 should be first with 10 karma (2 post likes * 5)
        self.assertEqual(leaderboard[0].username, 'alice')
        self.assertEqual(leaderboard[0].karma_24h, 10)
        
        # User2 should be second with 3 karma (3 comment likes * 1)
        self.assertEqual(leaderboard[1].username, 'bob')
        self.assertEqual(leaderboard[1].karma_24h, 3)
    
    def test_leaderboard_filters_old_karma(self):
        """
        Test that karma earned more than 24 hours ago is not counted.
        """
        # Create a post and like from user2
        post = Post.objects.create(author=self.user1, content="Old post")
        like = Like.objects.create(user=self.user2, post=post)
        
        # Manually set the karma transaction to be 25 hours old
        karma_tx = KarmaTransaction.objects.get(like=like)
        karma_tx.created_at = timezone.now() - timedelta(hours=25)
        karma_tx.save()
        
        # Get leaderboard
        leaderboard = KarmaTransaction.get_leaderboard(hours=24, limit=5)
        
        # User1 should NOT appear in leaderboard (karma is too old)
        self.assertEqual(len(leaderboard), 0)
    
    def test_leaderboard_limit(self):
        """
        Test that the leaderboard respects the limit parameter.
        """
        # Create 10 users with posts
        users = []
        for i in range(10):
            user = User.objects.create_user(username=f'user{i}', password='test123')
            users.append(user)
            post = Post.objects.create(author=user, content=f"Post {i}")
            Like.objects.create(user=self.liker, post=post)
        
        # Get top 5
        leaderboard = KarmaTransaction.get_leaderboard(hours=24, limit=5)
        
        # Should only return 5 users
        self.assertEqual(len(leaderboard), 5)
        
        # All should have 5 karma (1 post like)
        for user in leaderboard:
            self.assertEqual(user.karma_24h, 5)
    
    def test_leaderboard_ordering(self):
        """
        Test that users are correctly ordered by karma amount.
        """
        # User1: 1 post like = 5 karma
        post1 = Post.objects.create(author=self.user1, content="Post 1")
        Like.objects.create(user=self.liker, post=post1)
        
        # User2: 2 post likes = 10 karma
        post2 = Post.objects.create(author=self.user2, content="Post 2")
        Like.objects.create(user=self.user1, post=post2)
        Like.objects.create(user=self.user3, post=post2)
        
        # User3: 15 comment likes = 15 karma
        post3 = Post.objects.create(author=self.liker, content="Post 3")
        for i in range(15):
            comment = Comment.objects.create(post=post3, author=self.user3, content=f"Comment {i}")
            like = Like.objects.create(user=self.liker, comment=comment)
            # Make each like unique by creating different timestamps
            if i > 0:
                karma_tx = KarmaTransaction.objects.get(like=like)
                karma_tx.created_at = timezone.now() - timedelta(minutes=i)
                karma_tx.save()
        
        # Get leaderboard
        leaderboard = KarmaTransaction.get_leaderboard(hours=24, limit=5)
        
        # Verify correct ordering
        self.assertEqual(leaderboard[0].username, 'charlie')  # 15 karma
        self.assertEqual(leaderboard[0].karma_24h, 15)
        
        self.assertEqual(leaderboard[1].username, 'bob')  # 10 karma
        self.assertEqual(leaderboard[1].karma_24h, 10)
        
        self.assertEqual(leaderboard[2].username, 'alice')  # 5 karma
        self.assertEqual(leaderboard[2].karma_24h, 5)
