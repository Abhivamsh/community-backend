from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Prefetch, Count
from .models import Post, Comment, Like, KarmaTransaction
from .serializers import (
    PostSerializer, PostListSerializer, CommentSerializer,
    LikeSerializer, LeaderboardSerializer
)


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Post CRUD operations.
    Implements optimized querying to prevent N+1 problems.
    """
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """
        Optimize queries based on the action.
        For list: use lightweight query with select_related for author.
        For retrieve: prefetch ALL comments at once to avoid N+1.
        """
        if self.action == 'list':
            # List view: just posts with authors and like counts
            return Post.objects.select_related('author').annotate(
                like_count=Count('likes')
            )
        elif self.action == 'retrieve':
            # Detail view: prefetch entire comment tree in ONE query
            # This is the key to solving the N+1 nightmare
            comments_prefetch = Prefetch(
                'comments',
                queryset=Comment.objects.select_related('author').prefetch_related('replies').annotate(
                    like_count=Count('likes')
                )
            )
            return Post.objects.select_related('author').prefetch_related(
                comments_prefetch
            ).annotate(
                like_count=Count('likes')
            )
        else:
            return Post.objects.all()
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views."""
        if self.action == 'list':
            return PostListSerializer
        return PostSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single post with its full comment tree.
        The prefetch in get_queryset ensures we fetch all comments in 1-2 queries.
        """
        instance = self.get_object()
        
        # Attach all comments to instance for serializer
        # This allows the serializer to build the tree without additional queries
        instance.all_comments = list(instance.comments.all())
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def like(self, request, pk=None):
        """Like a post."""
        post = self.get_object()
        user_name = request.data.get('user_name', 'Anonymous')
        serializer = LikeSerializer(data={'post': post.id, 'user_name': user_name}, context={'request': request})
        
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({'status': 'post liked'}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Comment CRUD operations.
    """
    queryset = Comment.objects.select_related('author', 'post').prefetch_related('replies')
    serializer_class = CommentSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter comments by post if post_id is provided."""
        queryset = Comment.objects.select_related('author', 'post').annotate(
            like_count=Count('likes')
        )
        post_id = self.request.query_params.get('post_id')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def like(self, request, pk=None):
        """Like a comment."""
        comment = self.get_object()
        user_name = request.data.get('user_name', 'Anonymous')
        serializer = LikeSerializer(data={'comment': comment.id, 'user_name': user_name}, context={'request': request})
        
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({'status': 'comment liked'}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeaderboardViewSet(viewsets.ViewSet):
    """
    ViewSet for the leaderboard.
    Calculates top 5 users based on karma earned in the last 24 hours.
    """
    def list(self, request):
        """
        Get the top 5 users by karma in the last 24 hours.
        Uses the KarmaTransaction model for dynamic calculation.
        """
        leaderboard = KarmaTransaction.get_leaderboard(hours=24, limit=5)
        serializer = LeaderboardSerializer(leaderboard, many=True)
        return Response(serializer.data)
