<?php
declare(strict_types=1);
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
return new class extends Migration {
    public function up(): void {
        Schema::create('museum_inbound_requests', static function (Blueprint $table): void {
            $table->id();
            $table->string('external_id', 32)->unique();
            $table->string('kind', 16)->index();
            $table->text('payload'); // Laravel APP_KEY encryption at rest.
            $table->timestamp('received_at')->useCurrent();
            $table->timestamps();
        });
    }
    public function down(): void {Schema::dropIfExists('museum_inbound_requests');}
};
