<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('museum_media', static function (Blueprint $table): void {
            $table->id();
            $table->foreignId('museum_entry_id')->constrained('museum_entries')->cascadeOnDelete();
            $table->string('storage_path', 255)->unique();
            $table->string('sha256', 64);
            $table->string('alt', 255);
            $table->string('caption', 255)->nullable();
            $table->string('mime', 40)->default('image/webp');
            $table->unsignedInteger('width');
            $table->unsignedInteger('height');
            $table->unsignedInteger('size_bytes');
            $table->unsignedBigInteger('uploaded_by')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_media');
    }
};
