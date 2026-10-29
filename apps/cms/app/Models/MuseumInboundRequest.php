<?php
declare(strict_types=1);
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
final class MuseumInboundRequest extends Model {
    protected $fillable = ['external_id','kind','payload','received_at'];
    protected $hidden = ['payload'];
    public function getVisitorNameAttribute(): string {return (string)($this->payload['name'] ?? '');}
    public function getVisitorEmailAttribute(): string {return (string)($this->payload['email'] ?? '');}
    public function getVisitorMessageAttribute(): string {return (string)($this->payload['message'] ?? '');}
    public function getVisitorDateAttribute(): string {return (string)($this->payload['date'] ?? '');}
    public function getVisitorGroupAttribute(): string {return (string)($this->payload['group_size'] ?? '');}
    protected function casts(): array {
        return ['payload'=>'encrypted:array','received_at'=>'datetime'];
    }
}
