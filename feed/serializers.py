from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Count
from django.db import IntegrityError
from .models import Post, Comment, Like, KarmaTransaction



class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer."""
    
    class Meta:
        model = User
        fields = ['id', 'username']


# --------------------------------------------------
# RECURSIVE COMMENT SERIALIZER
# --------------------------------------------------

class RecursiveCommentSerializer(serializers.Serializer):
    """
    Handles unlimited nested replies.

    IMPORTANT:
    Efficient only if the view prefetches replies.
    """

    def to_representation(self, instance):
        serializer = CommentSerializer(
            instance,
            context=self.context,
            read_only=True
        )
        return serializer.data


# --------------------------------------------------
# COMMENT SERIALIZER
# --------------------------------------------------

class CommentSerializer(serializers.ModelSerializer):
    """
    Nested comment serializer with like count.
    """

    author = UserSerializer(read_only=True)
    author_name = serializers.CharField(write_only=True, required=True)

    like_count = serializers.IntegerField(read_only=True)
    replies = RecursiveCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id',
            'post',
            'parent',
            'author',
            'author_name',
            'content',
            'created_at',
            'like_count',
            'replies'
        ]
        read_only_fields = [
            'created_at',
            'like_count',
            'author'
        ]

    def create(self, validated_data):
        """
        Normalize username to avoid duplicates like:
        'Alex' vs 'alex'
        """
        author_name = validated_data.pop('author_name').strip().lower()

        author, _ = User.objects.get_or_create(
            username=author_name
        )

        validated_data['author'] = author
        return super().create(validated_data)


# --------------------------------------------------
# POST SERIALIZER (WITH NESTED COMMENTS)
# --------------------------------------------------

class PostSerializer(serializers.ModelSerializer):
    """
    Full post serializer including nested comments.

    SAFE only when comments are prefetched in the view.
    """

    author = UserSerializer(read_only=True)
    author_name = serializers.CharField(write_only=True, required=True)

    like_count = serializers.IntegerField(read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id',
            'author',
            'author_name',
            'content',
            'created_at',
            'like_count',
            'comments'
        ]
        read_only_fields = [
            'created_at',
            'like_count',
            'author'
        ]

    def get_comments(self, obj):
        """
        Return ONLY top-level comments.
        Replies handled recursively.
        """

        # If view attached prefetched comments
        if hasattr(obj, 'all_comments'):
            top_level = [
                c for c in obj.all_comments
                if c.parent_id is None
            ]

        else:
            # fallback (for create/update responses)
            top_level = obj.comments.filter(
                parent=None
            ).select_related(
                'author'
            ).annotate(
                like_count=Count('likes')
            )

        return CommentSerializer(
            top_level,
            many=True,
            context=self.context
        ).data

    def create(self, validated_data):

        author_name = validated_data.pop('author_name').strip().lower()

        author, _ = User.objects.get_or_create(
            username=author_name
        )

        validated_data['author'] = author
        return super().create(validated_data)


# --------------------------------------------------
# LIGHTWEIGHT POST SERIALIZER (FEED VIEW)
# --------------------------------------------------

class PostListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for feed.
    No nested comments → faster response.
    """

    author = UserSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id',
            'author',
            'content',
            'created_at',
            'like_count'
        ]
        read_only_fields = [
            'created_at',
            'like_count'
        ]


# --------------------------------------------------
# LIKE SERIALIZER
# --------------------------------------------------

class LikeSerializer(serializers.ModelSerializer):
    """
    Prevents double likes using DB constraints.
    """

    user_name = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Like
        fields = [
            'id',
            'user',
            'user_name',
            'post',
            'comment',
            'created_at'
        ]
        read_only_fields = [
            'user',
            'created_at'
        ]

    def validate(self, data):
        """
        Must like either post OR comment.
        """
        if not data.get('post') and not data.get('comment'):
            raise serializers.ValidationError(
                "Either post or comment must be provided."
            )

        if data.get('post') and data.get('comment'):
            raise serializers.ValidationError(
                "Cannot like both post and comment simultaneously."
            )

        return data

    def create(self, validated_data):

        user_name = validated_data.pop('user_name').strip().lower()

        user, _ = User.objects.get_or_create(
            username=user_name
        )

        validated_data['user'] = user

        try:
            return super().create(validated_data)

        except IntegrityError:
            raise serializers.ValidationError(
                "You have already liked this item."
            )


# --------------------------------------------------
# LEADERBOARD SERIALIZER
# --------------------------------------------------

class LeaderboardSerializer(serializers.Serializer):
    """
    Used for aggregated leaderboard query.
    """

    id = serializers.IntegerField()
    username = serializers.CharField()
    karma_24h = serializers.IntegerField()
