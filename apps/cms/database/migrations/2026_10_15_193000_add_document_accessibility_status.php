<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void {
        Schema::table('museum_documents', static function (Blueprint $table): void {
            $table->text('accessibility_note')->nullable();
            $table->boolean('accessibility_reviewed')->default(false);
        });
    }
    public function down(): void {
        Schema::table('museum_documents', static function (Blueprint $table): void {
            $table->dropColumn(['accessibility_note', 'accessibility_reviewed']);
        });
    }
};
