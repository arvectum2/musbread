<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // No names, emails, phone numbers, messages, IPs or other visitor PII.
        Schema::create('museum_requests', static function (Blueprint $table): void {
            $table->id();
            $table->string('reference', 40)->unique();
            $table->string('type', 32)->index();
            $table->string('topic', 40);
            $table->string('status', 20)->default('new')->index();
            $table->foreignId('museum_section_id')->nullable()
                ->constrained('museum_sections')->restrictOnDelete();
            $table->foreignId('assigned_to_id')->nullable()
                ->constrained('moonshine_users')->nullOnDelete();
            $table->date('preferred_date')->nullable();
            $table->unsignedSmallInteger('group_size')->nullable();
            $table->string('origin', 24)->default('internal_demo');
            $table->timestamp('resolved_at')->nullable();
            $table->timestamps();
            $table->index(['assigned_to_id', 'status']);
        });

        Schema::create('museum_request_transitions', static function (Blueprint $table): void {
            $table->id();
            $table->foreignId('museum_request_id')->constrained('museum_requests')->restrictOnDelete();
            $table->string('from_status', 20)->nullable();
            $table->string('to_status', 20);
            $table->foreignId('actor_id')->nullable()->constrained('moonshine_users')->nullOnDelete();
            $table->timestamp('created_at')->useCurrent();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('museum_request_transitions');
        Schema::dropIfExists('museum_requests');
    }
};
