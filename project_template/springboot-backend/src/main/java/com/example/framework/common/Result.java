package com.example.framework.common;

import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 统一响应结果
 */
@Data
public class Result<T> implements Serializable {
    
    private static final long serialVersionUID = 1L;
    
    /**
     * 是否成功
     */
    private Boolean success;
    
    /**
     * 响应码
     */
    private Integer code;
    
    /**
     * 响应消息
     */
    private String message;
    
    /**
     * 响应数据
     */
    private T data;
    
    /**
     * 时间戳
     */
    private LocalDateTime timestamp;
    
    public Result() {
        this.timestamp = LocalDateTime.now();
    }
    
    public Result(Boolean success, Integer code, String message, T data) {
        this.success = success;
        this.code = code;
        this.message = message;
        this.data = data;
        this.timestamp = LocalDateTime.now();
    }
    
    /**
     * 成功响应
     */
    public static <T> Result<T> success() {
        return new Result<>(true, 200, "操作成功", null);
    }
    
    public static <T> Result<T> success(T data) {
        return new Result<>(true, 200, "操作成功", data);
    }
    
    public static <T> Result<T> success(String message, T data) {
        return new Result<>(true, 200, message, data);
    }
    
    /**
     * 失败响应
     */
    public static <T> Result<T> error() {
        return new Result<>(false, 500, "操作失败", null);
    }
    
    public static <T> Result<T> error(String message) {
        return new Result<>(false, 500, message, null);
    }
    
    public static <T> Result<T> error(Integer code, String message) {
        return new Result<>(false, code, message, null);
    }
    
    /**
     * 分页响应
     */
    public static <T> Result<PageResult<T>> page(PageResult<T> pageResult) {
        return new Result<>(true, 200, "获取成功", pageResult);
    }
}