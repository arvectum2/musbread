<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('museum_entries', static function (Blueprint $table): void {
            $table->id();
            $table->string('type', 32)->index();
            $table->string('slug', 180)->unique();
            $table->string('title');
            $table->string('h1')->nullable();
            $table->string('parent_slug')->nullable();
            $table->text('excerpt')->nullable();
            $table->longText('body');
            $table->string('status', 20)->default('draft')->index();
            $table->timestamp('published_at')->nullable()->index();
            $table->string('seo_title')->nullable();
            $table->text('seo_description')->nullable();
            $table->unsignedInteger('sort_order')->default(0);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_entries');
    }
};
