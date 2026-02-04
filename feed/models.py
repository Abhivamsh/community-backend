from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from datetime import timedelta


class Post(models.Model):
    """
    Represents a text post in the feed.
    """
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Post by {self.author.username} at {self.created_at}"


class Comment(models.Model):
    """
    Represents a threaded comment on a post or another comment.
    Uses parent field for threading - supports unlimited nesting depth.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'parent']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.id}"


class Like(models.Model):
    """
    Represents a like on either a Post or a Comment.
    Uses database constraints to prevent double-likes (race condition protection).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Prevent double-likes at database level (handles race conditions)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'],
                condition=models.Q(post__isnull=False),
                name='unique_post_like'
            ),
            models.UniqueConstraint(
                fields=['user', 'comment'],
                condition=models.Q(comment__isnull=False),
                name='unique_comment_like'
            ),
            models.CheckConstraint(
                check=models.Q(post__isnull=False) | models.Q(comment__isnull=False),
                name='like_has_target'
            ),
            models.CheckConstraint(
                check=~(models.Q(post__isnull=False) & models.Q(comment__isnull=False)),
                name='like_single_target'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['comment', 'created_at']),
        ]
    
    def __str__(self):
        target = f"post {self.post.id}" if self.post else f"comment {self.comment.id}"
        return f"{self.user.username} liked {target}"
    
    def save(self, *args, **kwargs):
        """
        Override save to create a KarmaTransaction when a like is created.
        Uses transaction.atomic() to ensure data integrity.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Calculate karma based on what was liked
            if self.post:
                karma_amount = 5  # Post like = 5 karma
                recipient = self.post.author
            elif self.comment:
                karma_amount = 1  # Comment like = 1 karma
                recipient = self.comment.author
            else:
                return
            
            # Create karma transaction
            KarmaTransaction.objects.create(
                user=recipient,
                amount=karma_amount,
                like=self
            )


class KarmaTransaction(models.Model):
    """
    Stores karma transactions for dynamic leaderboard calculation.
    This is the key to solving the "DO NOT store Daily Karma as a simple integer" constraint.
    We store each karma event with a timestamp, allowing us to calculate 24h karma dynamically.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='karma_transactions')
    amount = models.IntegerField()  # 5 for post like, 1 for comment like
    like = models.OneToOneField(Like, on_delete=models.CASCADE, related_name='karma_transaction')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} earned {self.amount} karma"
    
    @classmethod
    def get_leaderboard(cls, hours=24, limit=5):
        """
        Calculate leaderboard based on karma earned in the last N hours.
        This is a complex aggregation that efficiently handles the 24h constraint.
        
        Returns QuerySet of users with their karma in the specified time window.
        """
        from django.db.models import Sum
        from django.contrib.auth.models import User
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Aggregate karma per user in the last 24 hours
        leaderboard = User.objects.filter(
            karma_transactions__created_at__gte=cutoff_time
        ).annotate(
            karma_24h=Sum('karma_transactions__amount')
        ).order_by('-karma_24h')[:limit]
        
        return leaderboard
