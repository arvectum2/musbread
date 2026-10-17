<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/** TZ-233: the editable public event and CMS section routes need own metadata. */
return new class extends Migration {
    public function up(): void
    {
        Schema::table('museum_events', static function (Blueprint $table): void {
            $table->string('h1', 255)->nullable();
        });
        Schema::table('museum_sections', static function (Blueprint $table): void {
            $table->string('h1', 255)->nullable();
            $table->string('seo_title', 255)->nullable();
            $table->text('seo_description')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('museum_sections', static function (Blueprint $table): void {
            $table->dropColumn(['h1', 'seo_title', 'seo_description']);
        });
        Schema::table('museum_events', static function (Blueprint $table): void {
            $table->dropColumn('h1');
        });
    }
};
