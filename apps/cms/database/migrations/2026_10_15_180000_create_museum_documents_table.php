<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('museum_documents', static function (Blueprint $table): void {
            $table->id();
            $table->foreignId('museum_entry_id')->constrained('museum_entries')->restrictOnDelete();
            $table->string('label', 180);
            $table->string('file_type', 8);
            $table->string('storage_path')->unique();
            $table->char('sha256', 64);
            $table->unsignedBigInteger('size_bytes');
            $table->foreignId('uploaded_by')->nullable()->constrained('moonshine_users')->nullOnDelete();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_documents');
    }
};
