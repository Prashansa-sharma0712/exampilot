import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.Base64;
import javax.imageio.ImageIO;
import org.apache.poi.hslf.usermodel.*;

// Apache POI preserves the presentation's slide order; no raw OLE atom guessing.
class LegacySlides {
    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[1]);
        Files.createDirectories(output);
        try (HSLFSlideShow deck = new HSLFSlideShow(new FileInputStream(args[0]));
             BufferedWriter writer = Files.newBufferedWriter(output.resolve("slides.tsv"), StandardCharsets.UTF_8)) {
            Dimension size = deck.getPageSize();
            int n = 0;
            for (HSLFSlide slide : deck.getSlides()) {
                ++n;
                StringBuilder text = new StringBuilder();
                for (java.util.List<HSLFTextParagraph> paragraph : slide.getTextParagraphs()) {
                    text.append(HSLFTextParagraph.getText(paragraph)).append("\n\n");
                }
                writer.write(n + "\t" + Base64.getEncoder().encodeToString(text.toString().getBytes(StandardCharsets.UTF_8)) + "\n");
                BufferedImage image = new BufferedImage(size.width * 2, size.height * 2, BufferedImage.TYPE_INT_RGB);
                Graphics2D graphics = image.createGraphics();
                graphics.setPaint(Color.WHITE);
                graphics.fillRect(0, 0, image.getWidth(), image.getHeight());
                graphics.scale(2, 2);
                graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
                slide.draw(graphics);
                graphics.dispose();
                ImageIO.write(image, "png", output.resolve("slide-" + n + ".png").toFile());
            }
            System.out.println("Extracted and rendered " + n + " slides");
        }
    }
}
