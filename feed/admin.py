from django.contrib import admin
from .models import Post, Comment, Like, KarmaTransaction


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'content_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'parent', 'content_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)


@admin.register(KarmaTransaction)
class KarmaTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'created_at')
    list_filter = ('created_at', 'amount')
    search_fields = ('user__username',)
