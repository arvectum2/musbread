<?php

namespace App\Support;

final class MuseumVideoUrlPolicy
{
    public static function safeEmbed(string $input):?string
    {
        if(strlen($input)>700 || str_contains($input, "\n") || str_contains($input,"\r")
            || str_contains($input,'#') || str_contains($input,'@'))return null;
        $parts=parse_url($input);
        if($parts===false||($parts['scheme']??'')!=='https'
            ||!in_array($parts['host']??'', ['vk.com','vkvideo.ru'],true)
            ||($parts['path']??'')!=='/video_ext.php'
            ||isset($parts['port'])||isset($parts['user'])||isset($parts['pass'])||isset($parts['fragment'])
            ||!isset($parts['query']))return null;
        $query=[];
        parse_str($parts['query'],$query);
        if(array_diff(array_keys($query),['oid','id','hd','hash'])!==[]
            ||!isset($query['oid'],$query['id'])
            ||!is_string($query['oid'])||!is_string($query['id'])
            ||!preg_match('/^-\d{1,12}$/D',$query['oid'])
            ||!preg_match('/^\d{5,16}$/D',$query['id'])
            ||isset($query['hd'])&&(!is_string($query['hd'])||!preg_match('/^[123]$/D',$query['hd']))
            ||isset($query['hash'])&&(!is_string($query['hash'])||!preg_match('/^[a-f0-9]{16,64}$/D',$query['hash']))
        )return null;
        return 'https://'.$parts['host'].'/video_ext.php?'.http_build_query($query,'','&',PHP_QUERY_RFC3986);
    }
    public static function sourceValid(string $input):bool
    {
        if(strlen($input)>700||str_contains($input,"\n")||str_contains($input,"\r"))return false;
        $parts=parse_url($input);
        return $parts!==false && ($parts['scheme']??'')==='https'
            && in_array($parts['host']??'', ['muzei-xleb.ru','vk.com','vkvideo.ru'],true)
            && !isset($parts['user']) && !isset($parts['pass'])
            && !isset($parts['port']) && !isset($parts['fragment']);
    }
}
