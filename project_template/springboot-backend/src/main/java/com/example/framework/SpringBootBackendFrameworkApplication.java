package com.example.framework;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;

/**
 * Spring Boot应用启动类
 */
@SpringBootApplication
@EnableCaching
@MapperScan("com.example.framework.mapper")
public class SpringBootBackendFrameworkApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootBackendFrameworkApplication.class, args);
        System.out.println("🚀 Spring Boot Backend Framework started successfully!");
    }
}