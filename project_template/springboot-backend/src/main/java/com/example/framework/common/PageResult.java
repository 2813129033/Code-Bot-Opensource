package com.example.framework.common;

import lombok.Data;
import java.io.Serializable;
import java.util.List;

/**
 * 分页结果
 */
@Data
public class PageResult<T> implements Serializable {
    
    private static final long serialVersionUID = 1L;
    
    /**
     * 当前页
     */
    private Long currentPage;
    
    /**
     * 每页大小
     */
    private Long pageSize;
    
    /**
     * 总页数
     */
    private Long totalPages;
    
    /**
     * 总记录数
     */
    private Long totalItems;
    
    /**
     * 是否有下一页
     */
    private Boolean hasNext;
    
    /**
     * 是否有上一页
     */
    private Boolean hasPrev;
    
    /**
     * 数据列表
     */
    private List<T> items;
    
    public PageResult() {
    }
    
    public PageResult(Long currentPage, Long pageSize, Long totalItems, List<T> items) {
        this.currentPage = currentPage;
        this.pageSize = pageSize;
        this.totalItems = totalItems;
        this.totalPages = (totalItems + pageSize - 1) / pageSize;
        this.hasNext = currentPage < totalPages;
        this.hasPrev = currentPage > 1;
        this.items = items;
    }
}