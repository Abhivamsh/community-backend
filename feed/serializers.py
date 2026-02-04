from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Count
from django.db import IntegrityError
from .models import Post, Comment, Like


# --------------------------------------------------
# USER
# --------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


# --------------------------------------------------
# HELPER FUNCTION (VERY IMPORTANT)
# --------------------------------------------------

def get_or_create_user(username):
    """
    Bulletproof username normalization.
    Prevents:
    - None.strip crash
    - empty usernames
    - case duplicates
    """
    if not username:
        raise serializers.ValidationError({
            "username": "Username is required."
        })

    username = username.strip().lower()

    if username == "":
        raise serializers.ValidationError({
            "username": "Username cannot be empty."
        })

    user, _ = User.objects.get_or_create(username=username)
    return user


# --------------------------------------------------
# RECURSIVE COMMENT SERIALIZER
# --------------------------------------------------

class RecursiveCommentSerializer(serializers.Serializer):
    def to_representation(self, instance):
        serializer = CommentSerializer(
            instance,
            context=self.context
        )
        return serializer.data


# --------------------------------------------------
# COMMENT SERIALIZER
# --------------------------------------------------

class CommentSerializer(serializers.ModelSerializer):

    author = UserSerializer(read_only=True)
    author_name = serializers.CharField(write_only=True)

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
        read_only_fields = ['author', 'created_at', 'like_count']

    def create(self, validated_data):

        username = validated_data.pop('author_name')
        user = get_or_create_user(username)

        validated_data['author'] = user
        return super().create(validated_data)


# --------------------------------------------------
# POST SERIALIZER
# --------------------------------------------------

class PostSerializer(serializers.ModelSerializer):

    author = UserSerializer(read_only=True)
    author_name = serializers.CharField(write_only=True)

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
        read_only_fields = ['author', 'created_at', 'like_count']

    def get_comments(self, obj):

        comments = obj.comments.filter(parent=None)\
            .select_related('author')\
            .annotate(like_count=Count('likes'))

        return CommentSerializer(
            comments,
            many=True,
            context=self.context
        ).data

    def create(self, validated_data):

        username = validated_data.pop('author_name')
        user = get_or_create_user(username)

        validated_data['author'] = user
        return super().create(validated_data)


# --------------------------------------------------
# LIGHTWEIGHT FEED SERIALIZER
# --------------------------------------------------

class PostListSerializer(serializers.ModelSerializer):

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


# --------------------------------------------------
# LIKE SERIALIZER
# --------------------------------------------------

class LikeSerializer(serializers.ModelSerializer):

    user_name = serializers.CharField(write_only=True)

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
        read_only_fields = ['user', 'created_at']

    def validate(self, data):

        if not data.get('post') and not data.get('comment'):
            raise serializers.ValidationError(
                "Either post or comment must be provided."
            )

        if data.get('post') and data.get('comment'):
            raise serializers.ValidationError(
                "Cannot like both post and comment."
            )

        return data

    def create(self, validated_data):

        username = validated_data.pop('user_name')
        user = get_or_create_user(username)

        validated_data['user'] = user

        try:
            return super().create(validated_data)

        except IntegrityError:
            raise serializers.ValidationError(
                "You already liked this."
            )


# --------------------------------------------------
# LEADERBOARD SERIALIZER
# --------------------------------------------------

class LeaderboardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    karma_24h = serializers.IntegerField()
