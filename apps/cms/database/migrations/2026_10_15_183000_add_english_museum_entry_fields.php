<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_entries', static function (Blueprint $table): void {
            $table->string('title_en')->nullable();
            $table->text('excerpt_en')->nullable();
            $table->longText('body_en')->nullable();
            $table->string('seo_title_en')->nullable();
            $table->text('seo_description_en')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('museum_entries', static function (Blueprint $table): void {
            $table->dropColumn([
                'title_en', 'excerpt_en', 'body_en', 'seo_title_en', 'seo_description_en',
            ]);
        });
    }
};
