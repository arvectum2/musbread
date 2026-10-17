<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('museum_fixed_page_seo', static function (Blueprint $table): void {
            $table->id();
            $table->string('path', 255)->unique();
            $table->string('seo_title', 255)->nullable();
            $table->text('seo_description')->nullable();
            $table->string('h1', 255)->nullable();
            $table->string('status', 16)->default('draft');
            $table->timestamps();
        });
        Schema::table('museum_entries', static function (Blueprint $table): void {
            $table->string('h1_en', 255)->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('museum_entries', static function (Blueprint $table): void {
            $table->dropColumn('h1_en');
        });
        Schema::dropIfExists('museum_fixed_page_seo');
    }
};
