<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void {
        Schema::table('museum_events', static function(Blueprint $table):void {
            $table->foreignId('cover_media_id')->nullable()
                ->constrained('museum_media')->nullOnDelete();
        });
    }
    public function down(): void {
        Schema::table('museum_events', static function(Blueprint $table):void {
            $table->dropConstrainedForeignId('cover_media_id');
        });
    }
};
