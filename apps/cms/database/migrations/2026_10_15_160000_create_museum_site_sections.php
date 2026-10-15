<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('museum_sections', static function (Blueprint $table): void {
            $table->id();
            $table->foreignId('parent_id')->nullable()->constrained('museum_sections')->restrictOnDelete();
            $table->string('slug', 180)->unique();
            $table->string('title');
            $table->unsignedInteger('sort_order')->default(0);
            $table->string('status', 20)->default('draft')->index();
            $table->string('legacy_path', 250)->nullable();
            $table->timestamps();
        });
        Schema::create('museum_section_editor', static function (Blueprint $table): void {
            $table->id();
            $table->foreignId('museum_section_id')->constrained('museum_sections')->cascadeOnDelete();
            $table->foreignId('moonshine_user_id')->constrained('moonshine_users')->cascadeOnDelete();
            $table->unique(['museum_section_id', 'moonshine_user_id']);
        });
        Schema::table('museum_entries', static function (Blueprint $table): void {
            $table->foreignId('museum_section_id')->nullable()->constrained('museum_sections')->restrictOnDelete();
        });
    }

    public function down(): void
    {
        Schema::table('museum_entries', static function (Blueprint $table): void {
            $table->dropConstrainedForeignId('museum_section_id');
        });
        Schema::dropIfExists('museum_section_editor');
        Schema::dropIfExists('museum_sections');
    }
};
